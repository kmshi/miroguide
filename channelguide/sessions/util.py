from datetime import datetime
import logging
import random

from sqlhelper import NotFoundError, NOW
from django.conf import settings

from channelguide import db, util
from models import Session

def delete_old_sessions():
    connection = db.connect()
    try:
        count = 0
        query = Session.query(Session.c.expires < NOW)
        for session in query.execute(connection):
            session.delete(connection)
            count += 1
        connection.commit()
        if count > 0:
            logging.info("Deleted %d old sessions" % count)
    finally:
        connection.close()

def make_new_session_key(connection):
    # This should be fairly secure as long as the random seed is not
    # possible to guess by an attacker.
    while 1:
        randstring = '%x' % random.getrandbits(128)
        key = util.hash_string(randstring + settings.SECRET_KEY)
        if Session.query(session_key=key).count(connection) == 0:
            return key

def get_session_from_key(connection, session_key):
    """Gets a session object using a session_key.  If session_key is
    None, doesn't exist in the DB or the session associated with it has
    expired a new Session will be created.
    """

    if session_key is None:
        return Session()
    try:
        session = Session.get(connection, session_key)
    except NotFoundError:
        return Session()
    if session.expires <= datetime.now():
        session.delete(connection)
        connection.commit()
        return Session()
    return session
