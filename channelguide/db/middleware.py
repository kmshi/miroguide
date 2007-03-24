from channelguide import db
from sqlalchemy import create_session

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

    def process_response(self, request, response):
        if hasattr(request, 'transaction') and request.transaction:
            request.transaction.commit()
        if hasattr(request, 'connection'):
            request.connection.close()
        return response

    def process_exception(self, request, exception):
        request.transaction.rollback()
        request.transaction = None
