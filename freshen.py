from channelguide import manage, init
init.init_external_libraries()
from channelguide.guide.views import channels
from channelguide.guide.models import user
from channelguide import db, cache
import time

cache.client.get = lambda x: None

database = db.connect()

def request(_method='GET', _path="/", **kwargs):
    class MockRequest:
        connection = database
        method = _method
        path = _path
        if _method == 'GET':
            GET = kwargs
        if _method == 'POST':
            POST = kwargs
        META = {'QUERY_STRING':''}
        # middleware would do this, but I'm lazy
        user = user.AnonymousUser()
        total_channels = 0
    return MockRequest()
while True:
    channels.popular(request(view='month'))
    print 'updated'
    time.sleep(60)
