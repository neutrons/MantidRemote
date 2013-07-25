from django.http import HttpResponse
from django.conf import settings

from models import Transaction

from MantidRemote.BasicAuthHelper import logged_in_or_basicauth

import datetime
import json
import os
import subprocess


def info( request):
    '''
    Returns basic information about the server.
    
    Note that this view does not require authentication.
    '''
    
    json_output = { }
    json_output['API_Version'] = settings.API_VERSION
    json_output['API_Extensions'] = settings.API_EXTENSIONS

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
def query( request):
    resp = HttpResponse()
    resp.write("<html>")
    resp.write("<H2>Congratulations!</H2></br>")
    resp.write("You've managed to call the query view.")
    resp.write("<hr>")

    # show some session info...
    resp.write("Session:</br>")
    resp.write("<ul>")
    keys = request.session.keys()
    keys.sort()
    for key in keys:
        resp.write("<li> %s: %s /<li>"%(key, request.session.get(key)))
        
    resp.write("</ul>")
    resp.write("<hr>")
    
    if 'flush' in request.GET.keys():
        # Flush the session
        resp.write ("Flushing session")
        resp.write( "<hr>")
        request.session.flush()
    
    # Play with sessions a bit - add a new key each time we're called
    num_keys = len(request.session.keys())
    new_key = "call_num_%d"%num_keys
    request.session[new_key]= str( datetime.datetime.now())  # @UndefinedVariable
    
    
    # display the request headers...
    resp.write("<ul>")
    for hdr in request.META:
        resp.write("<li> %s: %s /<li>"%(hdr, request.META[hdr]))
    
    resp.write("</ul>")
    resp.write("<br>")
    
    # display the query string
    resp.write("<ul>")
    for key in request.GET:
        resp.write("<li> %s: %s /<li>"%(key, request.GET[key]))
    
    resp.write("</ul>")
    resp.write("<br>")
    
    
    resp.write("</html>")
    return resp


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
    return json.dumps( out) 

# JSON output for some standard, oft-used error messages
def err_not_get():
    return json_err_msg("This URL only accepts 'GET' requests")

def err_not_post():
    return json_err_msg("This URL only accepts 'POST' requests")

def err_missing_param( param):
    return json_err_msg("Missing required parameter '%s'"%param)