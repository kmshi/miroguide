import logging

from sqlalchemy import create_session
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
        request.db_session = create_session(bind_to=request.connection)
        request.transaction = request.db_session.create_transaction()
        request.transaction.add(request.connection)
        # Hooking up to the request_finished signal seems like the most robust
        # way to close the connection.  Doing this in process_response doesn't
        # work in several cases, the most notable one is if the 404 template
        # is missing.
        dispatcher.connect(request.connection.close, 
                signal=signals.request_finished)

    def process_response(self, request, response):
        if hasattr(request, 'transaction') and request.transaction:
            request.transaction.commit()
        return response

    def process_exception(self, request, exception):
        request.transaction.rollback()
        request.transaction = None
