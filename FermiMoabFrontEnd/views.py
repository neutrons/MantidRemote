from django.http import HttpResponse
from django.conf import settings

from models import Transaction

from MantidRemote.BasicAuthHelper import logged_in_or_basicauth

import datetime
import json
import os.path
import os



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
        # TODO!! Call setfacl on the directory!!
        
        
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
        
        id = request.GET['TransID']
        
        # TODO: Implement this part!
        return HttpResponse( "Stopping transactions is not implemented, yet.", status=500)
        
        

