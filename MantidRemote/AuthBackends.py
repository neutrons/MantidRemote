# Holds classes for authenticating users.
# Will probably only be one class for now.

from django.conf import settings
from django.contrib.auth.models import User

import sys

# Need the python-ldap package
import ldap  # @UnresolvedImport

class SnsLdapBackend(object):
    """
    Authenticate against the SNS LDAP server.
    """
    # Note: As of July 2013, the SNS LDAP server's certificate is still signed with
    # the MD5 algorithm.  Newer version of openldap (including what's in RedHat 6.0
    # or later) will not accept the certificate by default.  The workaround is to 
    # set "NSS_HASH_ALG_SUPPORT=+MD5" in the python interpreter's environment.
    
    def authenticate(self, username=None, password=None):
        
        #build up the DN we need to bind to
        bind_dn = "uid=%s,ou=users,%s"%(username, settings.LDAP_BASE_DN);
        try:
            con = ldap.initialize(settings.LDAP_HOST)
            con.bind_s( bind_dn, password, ldap.AUTH_SIMPLE)
            search_results = con.search_s( settings.LDAP_BASE_DN, ldap.SCOPE_SUBTREE,
                                           settings.LDAP_FILTER)
            # The actual results come back as list who's single element is a tuple.
            # The tuple contains a string and a dictionary.  We want to look at the
            # memberUid element, who's value is list of all the user ID's that matched
            # the search.  We need to make sure username is in that list
            if not username in search_results[0][1]['memberUid']:
                return None

        except ldap.LDAPError, e:
            print >>sys.stderr,  "LDAP Exception (%s)"%e.__class__.__name__ 
            print >>sys.stderr, "Message(s):"
            for key in e.message:
                print >> sys.stderr, "%s: %s"%(key, e.message[key])
            sys.stderr.flush()
            return None

        except:
            return None
               
        # If we made it this far, we were able to bind to the ldap server and the
        # user has the proper permissions to submit jobs.  Fetch the user object
        # that's in the database (or create one, if necessary).
        # Note: Enough separate bits of Django require a user object to work
        # that we can't really avoid having one (which is automatically stored
        # in the database).  It might be a good idea to have a process that purges
        # users from the DB periodically just to keep the DB from growing too big.  
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Create a new user.  As mentioned above, authentication
            # is handled through LDAP, so we don't need to mess with
            # a password.
            user = User(username=username)
            user.is_staff = True
            user.is_superuser = False
            user.save()
        return user


    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
        
        
    
