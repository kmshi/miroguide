"""This is just a quick list of imports for when I'm running the shell.

Typical usage is:

    ./manage.py shell
    from channelguide.q import *

Or you can add some test statements at the end of this file run "python q.py".
"""
import manage

from sqlalchemy import *
from channelguide.channels.models import *
from channelguide import db
from channelguide.auth.models import User

from channelguide.channels.tables import *
from channelguide.auth.tables import *

sess = create_session(db.engine)
channels = sess.query(Channel).select(order_by=desc(Channel.c.modified))[:10]
tags = sess.query(Tag).select()[:10]
cats = sess.query(Category).select()[:10]
