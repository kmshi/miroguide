import logging
from sqlalchemy import create_session, func

from channelguide import db
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
