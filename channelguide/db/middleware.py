import logging

from django.dispatch import dispatcher
from django.core import signals

from channelguide import db

class DBMiddleware(object):
    """Adds a SQLAlchemy connection and session object to each request.
    
    Sessions will be automatically flushed in process_response().  Requests
    will be automitically closed.
    """

    def process_request(self, request):
        request.connection = db.connect()

    def process_response(self, request, response):
        if hasattr(request, 'connection'):
            request.connection.commit()
            request.connection.close()
            del request.connection
        return response

    def process_exception(self, request, exception):
        if hasattr(request, 'connection'):
            request.connection.rollback()
            request.connection.close()
            del request.connection
