import logging

from django.dispatch import dispatcher
from django.core import signals

from channelguide import db

class ConnectionCloser(object):
    def __init__(self, connection):
        self.connection = connection
        # Hooking up to the request_finished signal seems like the most robust
        # way to close the connection.  Doing this in process_response from a
        # middleware object doesn't work in several cases, the most notable
        # one is if the 404 template is missing.
        dispatcher.connect(self.close_connection,
                signal=signals.request_finished, weak=False)
    def close_connection(self):
        dispatcher.disconnect(self.close_connection,
                signal=signals.request_finished, weak=False)
        self.connection.close()

class DBMiddleware(object):
    """Adds a SQLAlchemy connection and session object to each request.
    
    Sessions will be automatically flushed in process_response().  Requests
    will be automitically closed.
    """

    def process_request(self, request):
        request.connection = db.connect()
        ConnectionCloser(request.connection)

    def process_response(self, request, response):
        try:
            connection = request.connection
        except AttributeError:
            pass
        else:
            connection.commit()
        return response

    def process_exception(self, request, exception):
        request.connection.rollback()
