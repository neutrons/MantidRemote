from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'MantidRemote.views.home', name='home'),
    # url(r'^MantidRemote/', include('MantidRemote.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)


# URL Patterns for the API
# The (?i) forces case insensitive matching
urlpatterns += patterns( 'FermiMoabFrontEnd.views',
    url(r'^(?i)info$', 'info', name='info_url'),
    url(r'^(?i)authenticate$', 'authenticate', name='authenticate_url'),
    url(r'^(?i)transaction$', 'transaction', name='transaction_url'),
    url(r'^(?i)download$', 'download', name='download_url'),
    url(r'^(?i)upload$', 'upload', name='upload_url'),
    url(r'^(?i)files$', 'files', name='files_url'),
    url(r'^(?i)submit$', 'submit', name='submit_url'),
#    url(r'^(?i)query$', 'query', name='query_url'),
)