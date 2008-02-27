# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

"""This is just a quick list of imports for when I'm running the shell.

Typical usage is:

    ./manage.py shell
    from channelguide.q import *

Or you can add some test statements at the end of this file run "python q.py".
"""
import manage
import time
import datetime
import itertools

from channelguide import init
init.init_external_libraries()
from channelguide import db
from channelguide.guide.models import *
from channelguide.guide.tables import *

connection = db.connect()
channel_q = Channel.query().order_by('modified', desc=True).limit(10)
channels = channel_q.execute(connection)
tags = Tag.query().limit(10).execute(connection)
cats = Category.query().limit(10).execute(connection)
