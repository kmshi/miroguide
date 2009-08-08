from simplejson import dumps
from django.http import HttpResponseNotAllowed, HttpResponse


#  Author:  http://www.djangosnippets.org/users/jerzyk/
def post_only(func):
    def decorated(request, *args, **kwargs):
        if request.method != 'POST':
            return HttpResponseNotAllowed('POST ONLY')
        return func(request, *args, **kwargs)
    return decorated

def get_only(func):
    def decorated(request, *args, **kwargs):
        if request.method != 'GET':
            return HttpResponseNotAllowed('GET ONLY')
        return func(request, *args, **kwargs)
    return decorated
