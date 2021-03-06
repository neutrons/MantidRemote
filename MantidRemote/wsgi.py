"""
WSGI config for MantidRemote project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os
import sys

sys.path.append('/var/www/MantidRemote')  # This needs to match where the app is actually deployed
#sys.path.append('/var/www/MantidRemote/MantidRemote')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MantidRemote.settings")

# Workaround so that we'll accept SNS's old, insecure LDAP certificate
os.environ['NSS_HASH_ALG_SUPPORT'] = '+MD5'

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)


# Import the werkzeug debugger so we can debug problems via the browsers
# NOTE: Do not include this code in production as it could allow any user
# to run arbitrary python code in the context of the web server!
#from werkzeug.debug import DebuggedApplication  # @UnresolvedImport
#application = DebuggedApplication(application, evalex=True)

def null_technical_500_response(request, exc_type, exc_value, tb):
    raise exc_type, exc_value, tb
from django.views import debug
debug.technical_500_response = null_technical_500_response
