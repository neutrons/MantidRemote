# Django settings for MantidRemote project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Ross Miller', 'rgmiller@ornl.gov'),
    ('Clay England', 'cluster-admins@ccs.ornl.gov')
)

MANAGERS = (
    ('Ross Miller', 'rgmiller@ornl.gov'),
)

#SERVER_EMAIL='django@fermi.ornl.gov'

# Email about broken links is only sent when NOT in debug mode
SEND_BROKEN_LINK_EMAILS = not DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '/home/xmr/workspace/MantidRemote/sqlite.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.4/ref/settings/#allowed-hosts
ALLOWED_HOSTS = [ '.ornl.gov', '.sns.gov', 'localhost']

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'p-24l91rewu1&amp;c63pd$a&amp;k0@dj_t&amp;1x5c0)rs*@&amp;84+u^9*=bb'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
# Disabling CSRF protection for the moment while I figure out if it can be
# made to work in the sort of RESTful environment I'm creating (ie, one
# where there's no template where the CSRF token can be initially 
# presented to the user) or if it's really necessary at all.
#    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'MantidRemote.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'MantidRemote.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'FermiMoabFrontEnd'
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

AUTHENTICATION_BACKENDS = (
   'MantidRemote.AuthBackends.SnsLdapBackend',
   'django.contrib.auth.backends.ModelBackend',
   # The normal auth method is to check the LDAP server.  We've
   # got the ModelBackend here so that we can add a couple of
   # admin users without having to set some extra fields in the
   # LDAP record.  Not entirely convinced this is a good idea, though.
)


# API version and supported extensions
# The info view will out this as JSON text
#
# This should be an integer.  We don't expect it to increase often/
API_VERSION = 1  
# A list of strings (ie: the names of the extensions).  Check the API doc
# to see what's been defined and what the names mean.
API_EXTENSIONS = [ 'JOB_DATES']


# Location of the 'scratch' directory where the server
# can create directories for each transaction
#TRANSACTION_DIR='/lustre/snsfs/scratch/apache'
TRANSACTION_DIR='/apache_files' # used for test/debug
# Note: For reasons that are unclear, apache doesn't seem
# to be allowed to write to /tmp.  It's not an selinux thing,
# so I'm guessing there's some default rules in the config
# file (or possibly it's hard-coded into apache itself?)

# Location of the setfacl binary
SETFACL_BIN='/usr/bin/setfacl'

# Values needed to talk to the LDAP server
LDAP_HOST = "ldaps://data.sns.gov/"
# Alternative host
# LDAP_HOST= "ldaps://data.sns.gov/"
LDAP_BASE_DN = "dc=sns,dc=ornl,dc=gov"
LDAP_FILTER = "(&(objectClass=posixGroup)(cn=SNS_Neutron))"


# Location & login info for the MWS server
#MWS_URL = "http://chadwick.sns.gov:8080/mws/rest"
#MWS_URL = 'http://fermi-mgmt3.ornl.gov:8080/mws/rest'
MWS_URL = 'http://127.0.0.1:8001/mws/rest'  # for testing with the MWS simulator
MWS_USER = "admin"                                                                                         
MWS_PASS = "5N5t3stBOX"
# TODO: fill in parameters for Fermi!!  
