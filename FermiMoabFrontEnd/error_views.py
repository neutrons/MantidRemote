'''
Created on Oct 3, 2013

@author: xmr

Two very simple views that handle 404 and 500 errors.  They output JSON
error messages that conform to the Mantid Remote Job Submission API.
Hopefully, they'll never actually be seen by anyone. 
'''

from django.http import HttpResponse

import json

def error_404( request):
    '''
    View for 404 errors.  Returns an error message encapsulated in a JSON string.
    '''
    
    json_output = { }
    json_output['Err_Msg'] = "URL not found. '%s' does not exist on this server." % request.path
    
    resp = HttpResponse( json.dumps(json_output), status=404)
    return resp

def error_500( request):
    '''
    View for 500 errors.  Returns an error message encapsulated in a JSON string.
    '''
    
    json_output = { }
    json_output['Err_Msg'] = "There was an internal problem with the server." + \
                             "  The administrators have been notified."
    
    resp = HttpResponse( json.dumps(json_output), status=500)
    return resp