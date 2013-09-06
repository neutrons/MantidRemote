from django.http import HttpResponse
from django.conf import settings

from models import Transaction, Job

from MantidRemote.BasicAuthHelper import logged_in_or_basicauth
from bash_script import generate_bash_script

import base64
import json
import os
import sys
import subprocess
import urllib2



def info( request):
    '''
    Returns basic information about the server.
    
    Note that this view does not require authentication.
    '''
    
    json_output = { }
    json_output['API_Version'] = settings.API_VERSION
    json_output['API_Extensions'] = settings.API_EXTENSIONS
    
    # Note: This value must match what the submit view requires! It'd be nice if
    # we could figure out a way to automatically keep it in sync with the submit view...
    json_output['Implementation_Specific_Submit_Variables'] = ['NumNodes', 'CoresPerNode']

    resp = HttpResponse( json.dumps(json_output))
    return resp
    

@logged_in_or_basicauth()
def authenticate( request):
    # This view doesn't actually do anything.  Enforcing the login is
    # actually handled by the decorator that's on all the views, but
    # the API specifies that the URL exist (mainly because other web
    # frameworks might need it).
    # If we ever accept something other than HTTP basic auth, we might
    # need do something here
    return HttpResponse()

@logged_in_or_basicauth()
def transaction( request):
    '''
    View for handling transaction start/stop

    <base_url>/transaction?Action=Start
    <base_url>/transaction?Action=Stop&TransID=<ID>
    '''
    
    # Validate the request
    if request.method != 'GET':
        return HttpResponse( err_not_get(),  status=400)  # Bad request
    
    if not 'Action' in request.GET:
        return HttpResponse( err_missing_param( 'Action'), status=400)  # Bad request
    
    action = request.GET['Action']
    if not (action == 'Start' or action == 'Stop'):
        return HttpResponse( json_err_msg("Expected either 'Start' or 'Stop' for the 'Action' parameter."),
                             status=400)
    if action == 'Start':
        # Start a new transaction
        new_trans = Transaction()
        new_trans.owner = request.user
        new_trans.save()  # Need to call save() so that the id value is generated

        # generate the name and create the directory
        dir_name = os.path.join( settings.TRANSACTION_DIR, request.user.username + '_' + str(new_trans.id))
        os.mkdir(dir_name, 0770)

        # Use setfacl to give the user read, write & execute permissions
        # on the directory we just created    
        permissions = request.user.username + ':rwX'
        proc = subprocess.Popen([settings.SETFACL_BIN, '-m', permissions, dir_name])
        proc.wait()
        if proc.returncode != 0:
            # couldn't set the ACL (maybe this filesystem doesn't support ACL's?)
            # so we need to fail the operation and that means cleaning up after
            # ourselves
            recursive_rm( dir_name)
            new_trans.delete()
            return HttpResponse( json_err_msg( "Cannot start transaction: Failed to set ACL's on transaction directory."),
                                 status=500) # internal server error

        # If we make it here, everything's good - save the transaction object
        # to the DB and return the required JSON        
        new_trans.directory = dir_name
        new_trans.save()
        
        json_out = { }
        json_out['TransID'] = new_trans.id
        json_out['Directory'] = dir_name
        return HttpResponse( json.dumps( json_out))
        
    else:
        # Stop an existing transaction
        # Need to specify the transaction ID
        (trans, error_response) = validate_trans_id( request)
        if error_response != None:
        # TransID didn't validate...
            return error_response
        
        # The transaction is validated - delete the files/directories
        recursive_rm( trans.directory)
        
        # delete the transaction from the db (Django defaults to 'cascaded' deletes,
        # so all we need to do is remove the transaction and everything that was pointing
        # to it (jobs & files) will also be removed
        trans.delete()
        
        return HttpResponse()
    
    
@logged_in_or_basicauth()
def download( request):
    '''
    View for downloading a specified file:
    <base_url>/download?&TransID=<ID>&File=<filename>
    
    Note that absolute paths aren't allowed.  <filename> must be relative to
    the directory that was created when the transaction was started.  In most
    cases, this means that there will be no path specified.  It's possible,
    however, for the submitted job to create a subdirectory under the
    transaction directory and write files there.  In such a case, the
    subdirectory will have to be included as part of <filename>.
    '''
    
    # Verify the that we have the proper request parameters
    # Validate the request
    if request.method != 'GET':
        return HttpResponse( err_not_get(), status=400)  # Bad request
    
    if not 'File' in request.GET:
        return HttpResponse( err_missing_param( 'File'), status=400)  # Bad request
    
    (trans, error_response) = validate_trans_id( request)
    if error_response != None:
        # TransID didn't validate...
        return error_response
    
    # compose the filename to transfer
    filename = os.path.join( trans.directory, request.GET['File'])
    try:
        resp = HttpResponse( open(filename).read(), content_type='application/octet-stream' )
        resp['Content-Disposition'] = 'attachment; filename="%s"'%request.GET['File']
    except IOError, msg:
        if msg.errno == 2:  # Errno 2 is a 'file not found'
            json_out = json_err_msg( "Could not find a file named %s associated with transaction %s"%(request.GET['File'],trans.id))
        else:
            json_out = json_err_msg( "Unknown error attempting to download %s"%request.GET['File'])
        resp = HttpResponse(json_out, status=400)
    return resp


@logged_in_or_basicauth()
def upload( request):
    '''
    View for uploading a file.  This should be a POST request.
    '''
    
    # Verify the request method, the FILES dict and TransID parameter
    if request.method != 'POST':
        return HttpResponse( err_not_post(), status=400) # Bad request
    
    if len(request.FILES.keys()) == 0:
        return HttpResponse( json_err_msg( "No files specified to upload"), status=400)
    
    (trans, error_response) = validate_trans_id( request)
    if error_response != None:
        return error_response
    
    # Save each file in the FILES dictionary
    for filename in request.FILES:
        pathname = os.path.join(trans.directory, filename)
        new_file = open( pathname, mode='wb')
        new_file.write( request.FILES[filename].read())
        new_file.close()
        
    return HttpResponse( status=201)  # Returning '201 CREATED'


@logged_in_or_basicauth()
def files( request):
    '''
    View for displaying files that are associated with a particular transaction.
    '''
    # Verify the that we have the proper request parameters
    if request.method != 'GET':
        return HttpResponse( err_not_get(), status=400)  # Bad request
    
    (trans, error_response) = validate_trans_id( request)
    if error_response != None:
        # TransID didn't validate...
        return error_response

    # recurse through the dir hierarchy (in most cases there
    # will be no subdirs, but we'll support them having them)
    files = [ ]
    dirs = os.walk( trans.directory)
    for one_dir in dirs:
        # Remove the parts of the path that include the transaction directory
        # (and everything above it) because we don't want to expose this data
        # to users
        subpath = one_dir[0][len(trans.directory)+1:]
        for f in one_dir[2]:
            files.append( os.path.join(subpath, f))
    
    files.sort()  # Not sure this is really helpful, but it probably doesn't hurt
    json_out = { 'Files' : files}
    return HttpResponse( json.dumps(json_out), status=200)
    
    
@logged_in_or_basicauth()
def submit( request):
    # Verify the that we have the proper request parameters
    if request.method != 'POST':
        return HttpResponse( err_not_get(), status=400)  # Bad request
    
    (trans, error_response) = validate_trans_id( request)
    if error_response != None:
        # TransID didn't validate...
        return error_response
    
    if not 'NumNodes' in request.POST:
        return HttpResponse( err_missing_param( 'NumNodes'), status=400)  # Bad request
    
    if not 'CoresPerNode' in request.POST:
        return HttpResponse( err_missing_param( 'CoresPerNode'), status=400)  # Bad request
    
    # Verify the request parameters for the python script
    if not 'ScriptName' in request.POST:
        return HttpResponse( err_missing_param( 'ScriptName'), status=400)  # Bad request
    
    script_name = request.POST['ScriptName']
    if not script_name in request.POST:
        return HttpResponse( "Expected POST variable %s not received"%script_name, status=400)  # Bad request
       
    # Make sure we don't overwrite an existing script with a new one of the same name
    # TODO: Technically, this is a race condition: it's theoretically possible for a user
    # to send 2 requests simultaneously with the same script name and have one overwritten
    # because neither existed at the time isfile() was called.  Not sure what to do about
    # this: some web servers spawn multiple processes, so a regular mutex or critical
    # section won't help.
    full_script_name = os.path.join( trans.directory, script_name)
    file_num=0
    while (os.path.isfile( full_script_name)):
        file_num += 1
        full_script_name = os.path.join( trans.directory, "%s-%d"%(script_name, file_num))
    
    # Save the uploaded python script to the transaction directory    
    script_file = open( full_script_name, 'w')
    script_file.write( request.POST[script_name])
    script_file.close() 

    # Generate the bash script that will actually be run by Moab/Torque
    # TODO: see the comments above about the race condition with file names
    submit_file_name = os.path.join( trans.directory, 'submit.sh')
    file_num=0
    while (os.path.isfile( submit_file_name)):
        file_num += 1
        submit_file_name = os.path.join( trans.directory, 'submit.sh-%d'%file_num) 
    submit_file = open(submit_file_name, 'w')
    submit_file.write( generate_bash_script( NUM_NODES=request.POST['NumNodes'],
                                             CORES_PER_NODE=request.POST['CoresPerNode'],
                                             TRANSACTION_DIRECTORY=trans.directory,
                                             PYTHON_JOB_SCRIPT=script_name))
    submit_file.close()
    
    # Generate the JSON that's submitted to Moab Web Services
    submit_json = {}
    submit_json['commandFile'] =  "/bin/bash"
    submit_json['commandLineArguments'] = submit_file.name
    submit_json['user'] = request.user.username
    submit_json['group'] = 'users'
    
    # The job name parameter is optional
    if 'JobName' in request.POST:
        submit_json['name'] = request.POST['JobName']
    else:
        submit_json['name'] = "Unknown"
    
    submit_json['requirements'] = [ {"requiredProcessorCountMinimum": request.POST['NumNodes']} ]
    # Yes, this is confusing, but the way we've got Moab configured on Femi,
    # requiredProcessorCountMinimum actually specifies the number of NODES
    # that are reserved for the job.
    # Also, for reasons that have never been clear, MWS wants the requirements field to be a list
    # containing a single object (instead of just the object itself...)
    
    # This isn't necessary for Moab to schedule the job.  However, by setting the variable,
    # we can distinguish between jobs that were submitted via this mechanism and stuff that
    # the user might have just qsub'd...
    # Note: Last I knew, a bug in MWS meant these variables were forgotten.  Not sure if this
    # has been fixed yet. 
    submit_json['variables'] = {"JOB_TYPE":"Mantid"}
    submit_json['standardErrorFilePath'] = trans.directory
    submit_json['standardOutputFilePath'] = trans.directory
    
    # This is just an example so I remember how to set environment variables in case I
    # ever need to.  Leave it commented out.
    #submit_json['environmentVariables'] = {"MANTIDPLOT_NUM_NODES" : request.POST['NumNodes']}
    
    # Make the HTTP call
    return_code,json_result = mws_request(settings.MWS_URL + "/jobs", submit_json)
    if return_code == 201:
        # Success Return the Job ID to the user
        json_out = { }
        json_out['JobID'] = json_result['id']
        
        # Add the job object to the local db
        new_job = Job()
        new_job.transaction = trans
        new_job.script_name = script_name
        new_job.mws_job_id = json_result['id'];
        new_job.save()
    else:
        json_out = { }
        json_out['Err_Msg'] = "Error returned from Moab Web Services"
        json_out['MWS_Err_Msg'] = json_result   
        
    return HttpResponse( json.dumps(json_out, indent=2), status=return_code)
    

@logged_in_or_basicauth()
def abort( request):
    '''
    View for aborting a previously submitted job
    '''
    
    # Verify the that we have the proper request parameters
    if request.method != 'GET':
        return HttpResponse( err_not_get(), status=400)  # Bad request
    
    if 'JobID' in request.GET:
        # Check to see if the requested job ID is valid (ie, it exists and it
        # was submitted by the current user
        (job, error_response) = validate_job_id( request)
        if error_response != None:
            # The JobID didn't validate...
            return error_response 
    
    abort_url = settings.MWS_URL + '/jobs/' + request.GET['JobID']
    return_code,json_result = mws_request( abort_url, None, 'DELETE')
    
    json_out = { }
    if return_code != 200:
        # The MWS docs don't explicitly mention exactly what will be returned if there's
        # an error.  From testing, it appears to be the same structure as the error returned
        # when a job submit fails.       
        json_out['Err_Msg'] = "Error returned from Moab Web Services"
        json_out['MWS_Err_Msg'] = json_result["messages"]
        
    return HttpResponse( json.dumps(json_out, indent=2), status=return_code)    
    
    
@logged_in_or_basicauth()
def query( request):
    '''
    View for displaying info about 1 specific job or all of a user's jobs
    '''
    
    # Verify the that we have the proper request parameters
    if request.method != 'GET':
        return HttpResponse( err_not_get(), status=400)  # Bad request
    
    # There's two forms of this view: one for querying all of a user's jobs
    # and one for just querying a specific job
    query_url = settings.MWS_URL + "/jobs"
    if 'JobID' in request.GET:
        # Check to see if the requested job ID is valid (ie, it exists and it
        # was submitted by the current user
        (job, error_response) = validate_job_id( request)
        if error_response != None:
            # The JobID didn't validate...
            return error_response 
        
        # query url for one job
        query_url += "/" + request.GET['JobID']
    
    return_code,json_result = mws_request(query_url)
    
    if return_code == 200:
        # Success! Parse the returned JSON for the data we want
        # Note: If we requested all jobs, then the data is buried a 
        # couple levels deeper than if we only requested a specific job
        if 'JobID' in request.GET:
            jobs = [ ]
            jobs.append( json_result)
        else:
            jobs = json_result['results']
            
        # Note: the results for a single job query are considerably more
        # detailed than those returned by the 'query all jobs' request.
        json_out = { }
        for job in jobs:
            # First, filter out all the jobs from other users
            if job['user'] == request.user.username:
                try:
                    job_obj = Job.objects.get( mws_job_id = job['id'])
                    job_data = { }
                    job_data['JobName'] = job['name']
                    job_data['JobStatus'] = job['state']
                    
                    # Transaction ID and script name come from the local db.
                    # (Moab Web Services has no concept of either.)
                    job_data['TransID'] = job_obj.transaction.id
                    job_data['ScriptName'] = job_obj.script_name
                    
                    json_out[job['id']] = job_data
                except Job.DoesNotExist:
                    # We don't return data for jobs not in our local db.
                    # Assuming it's not a bug of some kind, then such jobs
                    # were not submitted through this web service and we're
                    # not going to try to manage them.
                    # Or, the user already ended the transaction and we're just
                    # waiting for MWS to forget about them on its own
                    pass
    
    else:  # MWS returned something other than 200
        # The MWS docs don't explicitly mention exactly what will be returned if there's
        # an error.  From testing, it appears to be the same structure as the error returned
        # when a job submit fails. 
        json_out = { }      
        json_out['Err_Msg'] = "Error returned from Moab Web Services"
        json_out['MWS_Err_Msg'] = json_result["messages"]
    
    return HttpResponse( json.dumps(json_out, indent=2), status=return_code)
    
    


def mws_request( url, post_data=None, request_type=None):
    '''
    Sends an HTTP (or HTTPS) request to the MWS server and returns the results.
    
    Used as a helper by several view funtions
    
    url is a string
    post_data can be any type.  If it's not None, it will be converted to a JSON string
    
    Returns the http status code and a dictionary containing any JSON data that was returned from MWS
    '''
    
    # NOTE: There's a warning in the urllib2 docs saying that it does not verify the
    # server's certificate when making HTTPS connections
    
    req = urllib2.Request(url)
    
    # by default, urllib2 will generate either a GET or a POST request for http
    # urls (depending on whether any post data exists).  In certain cases, we
    # might want to do something else (DELETE, for example).  Replacing the
    # get_method function with one that returns the method we want to use seems like
    # a dirty hack, but it appears to work...
    if (request_type):
        req.get_method = lambda: request_type
        
    encoded_pwd = base64.b64encode( '%s:%s'%(settings.MWS_USER, settings.MWS_PASS))
    req.add_header('Authorization', 'Basic %s'%encoded_pwd)
    try:
        if post_data != None:
            req.add_header( "Content-Type", "application/json")
            # Note: Passing anything to the data field of the urlopen() function
            # means the function will make a POST request instead of a GET request.
            # This is exactly the behavior we want.
            result = urllib2.urlopen(req, json.dumps(post_data))
        else:
            result = urllib2.urlopen(req)
            
        json_result = json.loads( result.read())
        status_code = result.getcode()
    except urllib2.HTTPError, e:
        # urllib2 seems to throw these in any case where the status code
        # was not 2xx
        json_result = json.load(e) # calls e.read()...
        print >>sys.stderr, "Error returned from MWS server.  Code: %d"%e.code       
        print >>sys.stderr,  "Message returned from MWS:"
        json.dump(json_result, sys.stderr, indent=2)
        sys.stderr.flush()
        status_code = e.code;
    
    return status_code, json_result


def recursive_rm( dirname):
    '''
    Delete all files and directories under the specified directory - including
    the specified directory itself.  Effectively identical to 'rm -r <dirname>'
    
    Helper for the transaction view.
    '''
    dirs = os.walk( dirname)
    dirnames = []
    for item in dirs:
        dirnames.append(item[0])
        for filename in item[2]:
            path = os.path.join( item[0], filename)
            os.remove(path)
    
    # That takes care of the files, now to remove the directories
    # Sort the full pathnames by length.  Calling rmdir the longest paths
    # first ensures we remove any child dir before removing its parent
    dirnames.sort()
    for i in range(len(dirnames)-1, -1, -1):
        os.rmdir(dirnames[i])

def validate_job_id( request):
    '''
    Verify that the specified job ID exists and is owned by the current user.
    
    Returns a tuple of the job object from the database (if everything
    validated) and an HttpResponse object (if there was an error).  One of the
    items in the tuple will be None.
    
    Helper function for the query view
    '''
    if not 'JobID' in request.GET:
        return (None, HttpResponse( err_missing_param( 'JobID'), status=400))  # Bad request
    
    try:
        job = Job.objects.get( mws_job_id = request.GET['JobID'])
    except Job.DoesNotExist:
        return (None, HttpResponse( json_err_msg("Job '%s' does not exist"%request.GET['JobID']),
                                    status = 400))
        
    if job.transaction.owner.username != request.user.username:
        # TODO: can we just compare owner to user instead of going all the way down to the username level?
        # Note: This is a bit of security concern since we effectively 
        # acknowledge the existence of a job the user doesn't own.  Should we
        # return a 'does not exist' error instead?
        return (None, HttpResponse( json_err_msg("Job '%s' is not owned by "%request.user.username),
                                    status = 400)) 
    return(job, None)
    
def validate_trans_id( request):
    '''
    Verify that a transaction ID was specified, that the transaction exists
    and that it's owned by the current user.
    
    Returns a tuple of the transaction object from the database (if everything
    validated) and an HttpResponse object (if there was an error).  One of the
    items in the tuple will be None.
    
    Helper function for several views.
    '''
    
    # Need to specify the transaction ID
    if request.method == 'GET':
        if not 'TransID' in request.GET:
            return (None, HttpResponse( err_missing_param( 'TransID'), status=400))  # Bad request
        trans_id = request.GET['TransID']
    else:
        if not 'TransID' in request.POST:
            return (None, HttpResponse( err_missing_param( 'TransID'), status=400))  # Bad request
        trans_id = request.POST['TransID']
    
    try:        
        trans = Transaction.objects.get( id=trans_id)
    except Transaction.DoesNotExist:
        return (None, HttpResponse( json_err_msg( "Transaction '%s' does not exist"%trans_id),
                                    status=400))  # Bad request
            
    # verify the id we're trying to stop is owned by the user
    if trans.owner != request.user:
        return (None, HttpResponse( json_err_msg( "Transaction '%s' is not owned by the current user"%trans_id),
                                    status=400))  # Bad request
    
    return (trans, None)
    
    
def json_err_msg( msg):
    '''
    Generates the proper JSON string for returning the specified error message in an HttpResponse object.
    '''
    # The name 'Err_Msg' is defined by the API doc
    out = { "Err_Msg" : msg}
    return json.dumps( out, indent=2) 

# JSON output for some standard, oft-used error messages
def err_not_get():
    return json_err_msg("This URL only accepts 'GET' requests")

def err_not_post():
    return json_err_msg("This URL only accepts 'POST' requests")

def err_missing_param( param):
    return json_err_msg("Missing required parameter '%s'"%param)
