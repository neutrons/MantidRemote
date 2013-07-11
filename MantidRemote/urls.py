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
urlpatterns += patterns( 'FermiMoabFrontEnd.views',
    url(r'^query$', 'query', name='query_url'),
)