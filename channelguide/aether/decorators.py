#
#  Author:  http://www.djangosnippets.org/users/jerzyk/
#
 
from django.http import HttpResponseNotAllowed

# decorators
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
