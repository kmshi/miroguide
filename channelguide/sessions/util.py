from datetime import datetime
import logging
import random

from django.conf import settings
from sqlalchemy import create_session, func

from channelguide import db, util
from models import Session

def delete_old_sessions():
    db_session = create_session(bind_to=db.engine)
    query = db_session.query(Session)
    count = 0
    for session in query.select(Session.c.expires < func.now()):
        db_session.delete(session)
        count += 1
    if count > 0:
        db_session.flush()
        logging.info("Deleted %d old sessions" % count)

def make_new_session_key(db_session):
    # This should be fairly secure as long as the random seed is not
    # possible to guess by an attacker.
    while 1:
        randstring = '%x' % random.getrandbits(128)
        key = util.hash_string(randstring + settings.SECRET_KEY)
        if db_session.get(Session, key) is None:
            return key

def get_session_from_key(db_session, session_key):
    """Gets a session object using a session_key.  If session_key is
    None, doesn't exist in the DB or the session associated with it has
    expired a new Session will be created.
    """

    if session_key is None:
        return Session()
    session = db_session.get(Session, session_key)
    if session is None:
        return Session()
    if session.expires < datetime.now():
        db_session.delete(session)
        return Session()
    return session
