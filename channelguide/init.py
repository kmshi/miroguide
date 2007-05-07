"""Contains code needed to initialize channelguide.  This should be run at
startup, before any real work starts.
"""

import logging
import logging.handlers
import random
import os
import sys
import traceback

from django.conf import settings
from django.core import signals
from django.dispatch import dispatcher

def init_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    log_path = os.path.join(settings.SITE_DIR, 'log', 'cg.log')
    handler = logging.handlers.RotatingFileHandler(log_path, maxBytes=2**20)
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(handler)

def log_error():
    logging.error("Unhandled Exception: %s", traceback.format_exc())

def init_external_libraries():
    sys.path.insert(0, settings.EXTERNAL_LIBRARY_DIR)

def initialize():
    init_logging()
    dispatcher.connect(log_error, signal=signals.got_request_exception)
    init_external_libraries()
    random.seed()
