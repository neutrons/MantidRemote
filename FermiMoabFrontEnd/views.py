from django.http import HttpResponse


#def authenticate( request):
#    # Check the HTTP BasicAuth header...
    
def query( request):
    resp = HttpResponse()
    resp.write("<html>")
    resp.write("<H2>Congratulations!</H2></br>")
    resp.write("You've managed to call the query view.")
    resp.write("<hr>")
    
    # display the request headers...
    resp.write("<ul>")
    for hdr in request.META:
        resp.write("<li> %s: %s /<li>"%(hdr, request.META[hdr]))
    
    resp.write("</ul>")
    resp.write("<br>")
    resp.write("</html>")
    return resp
