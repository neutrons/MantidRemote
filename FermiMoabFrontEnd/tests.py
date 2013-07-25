"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.test.client import Client

import json
import base64

TEST_USER = 'test_user'
TEST_PWD = 'test_pwd'
auth_string = "Basic %s"%base64.b64encode("%s:%s"%(TEST_USER,TEST_PWD))

class FermiTestCase( TestCase):
    def setUp(self):
        # Add a user to the test database so we can log in and do things...
        User.objects.create_user( TEST_USER, password=TEST_PWD)
    
    def test_info(self):
        c = Client()
        response = c.get( '/info')
        self.assertContains(response, '{', status_code=200)
        result = json.loads(response.content)
        self.assertIn('API_Version', result)
        self.assertIn('API_Extensions', result)
        self.assertEqual( result['API_Version'], 0)
        self.assertEqual( len( result['API_Extensions']), 0)
        
    def test_authenticate(self):
        c = Client()
        response = c.get( '/authenticate', HTTP_AUTHORIZATION=auth_string)
        self.assertContains( response, '', status_code=200)
        self.assertEqual(len(response.content), 0)
    
    def test_transactions(self):
        c = Client()
        response = c.get( '/transaction', HTTP_AUTHORIZATION=auth_string)
        self.assertContains( response, '', status_code=400)
        result = json.loads(response.content)
        self.assertIn( 'Err_Msg', result)
        self.assertEqual(result['Err_Msg'], "Missing required parameter 'Action'")
        
        response = c.get( '/transaction?Action=Bogus', HTTP_AUTHORIZATION=auth_string)
        self.assertContains( response, '', status_code=400)
        result = json.loads(response.content)
        self.assertIn( 'Err_Msg', result)
        self.assertEqual(result['Err_Msg'], "Expected either 'Start' or 'Stop' for the 'Action' parameter.")

# Unfortunately, this test actually returns a 500 because it can't
# set the ACL for a non-existent user.
#        response = c.get( '/transaction?Action=Start', HTTP_AUTHORIZATION=auth_string)
#        self.assertContains( response, '', status_code=200)
#        result = json.loads(response.content)
#        self.assertIn( 'TransID', result)
#        trans_id = result['TransID']  # Save the ID so we can kill the transaction
        
        response = c.get( '/transaction?Action=Stop', HTTP_AUTHORIZATION=auth_string)
        self.assertContains( response, '', status_code=400)
        result = json.loads(response.content)
        self.assertIn( 'Err_Msg', result)
        self.assertEqual(result['Err_Msg'], "Missing required parameter 'TransID'")
        
        response = c.get( '/transaction?Action=Stop&TransID=99999', HTTP_AUTHORIZATION=auth_string)
        self.assertContains( response, '', status_code=400)
        result = json.loads(response.content)
        self.assertIn( 'Err_Msg', result)
        self.assertEqual(result['Err_Msg'], "Transaction '99999' does not exist")

# Since we never successfully started a transaction, there's nothing to stop        
#        response = c.get( '/transaction?Action=Stop&TransID=%s'%trans_id, HTTP_AUTHORIZATION=auth_string)
#        self.assertContains( response, '', status_code=200)
#        self.assertEqual(len(response.content), 0)
        

