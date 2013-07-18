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
    
    # Include the min/max acceptable API versions  in the output
    json_output['API_Versions'] = settings.API_VERSIONS
    
    resp = HttpResponse( json.dumps(json_output))

    return resp
    

@logged_in_or_basicauth()
def authenticate( request):
    # This view doesn't actually do anything.  Enforcing the login is
    # actually handled by the decorator above, but the API specifies
    # that the URL exist (mainly because other web frameworks might
    # need it).
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
        return HttpResponse( status=400)  # Bad request
    
    if not 'Action' in request.GET:
        return HttpResponse( status=400)  # Bad request
    
    action = request.GET['Action']
    if not (action == 'Start' or action == 'Stop'):
        return HttpResponse( status=400)
    
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
            return HttpResponse( status=500) # internal server error

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
        if not 'TransID' in request.GET:
            return HttpResponse( status=400)  # Bad request
        
        trans_id = request.GET['TransID']
        trans = Transaction.objects.get( id=trans_id)
                
        # verify the id we're trying to stop is owned by the user
        if trans.owner != request.user:
            return HttpResponse( status=400) 
        
        # The transaction is validated - delete the files/directories
        recursive_rm( trans.directory)
        
        # delete the transaction from the db (Django defaults to 'cascaded' deletes,
        # so all we need to do is remove the transaction and everything that was pointing
        # to it (jobs & files) will also be removed
        trans.delete()
        
        return HttpResponse()
    

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
    
    
