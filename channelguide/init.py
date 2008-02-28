# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

"""Contains code needed to initialize channelguide.  This should be run at
startup, before any real work starts.
"""

import locale
import logging
import logging.handlers
import random
import os
import socket
import sys
import traceback

from django.conf import settings
from django.core import signals
from django.dispatch import dispatcher
import django.db

def init_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    log_path = os.path.join(settings.SITE_DIR, 'log', 'cg.log')
    handler = logging.handlers.RotatingFileHandler(log_path, maxBytes=2**20)
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(handler)

def init_external_libraries():
    sys.path.insert(0, settings.EXTERNAL_LIBRARY_DIR)
    from django.utils.translation import ugettext
    __builtins__['_'] = ugettext

def initialize():
    init_logging()
    init_external_libraries()
    random.seed()
    locale.setlocale(locale.LC_ALL, '')
    socket.setdefaulttimeout(settings.SOCKET_TIMEOUT)

    # hack for the fact that django tries to rollback its non-existant
    # connection when requests finish.
    dispatcher.disconnect(django.db._rollback_on_exception, 
        signal=signals.got_request_exception)

