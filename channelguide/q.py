"""This is just a quick list of imports for when I'm running the shell.

Typical usage is:

    ./manage.py shell
    from channelguide.q import *

Or you can add some test statements at the end of this file run "python q.py".
"""
import manage

from sqlalchemy import *
from channelguide import db
from channelguide.guide.models import *
from channelguide.guide.tables import *

connection = db.connect()
sess = create_session(connection)
channels = sess.query(Channel).select(order_by=desc(Channel.c.modified))[:10]
tags = sess.query(Tag).select()[:10]
cats = sess.query(Category).select()[:10]
