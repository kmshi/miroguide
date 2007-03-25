import manage # must be 1st because it sets up sys.path

import logging
import logging.handlers
import os
import sys
import time

from django.conf import settings
from sqlalchemy import create_session

from channelguide import db, tasks, sessions
from channelguide.tasks.decorators import run_every_hour, run_every_day

@run_every_hour
def delete_old_sessions():
    logging.info('Deleting old sessions')
    sessions.delete_old_sessions()

@run_every_hour
def delete_old_thumbnails():
    logging.info('Deleting old thumbnails')
    media_tmp_dir = os.path.join(settings.MEDIA_ROOT, 'tmp')
    one_day = 60 * 60 * 24
    for filename in os.listdir(media_tmp_dir):
        path = os.path.abspath(os.path.join(media_tmp_dir, filename))
        if os.stat(path).st_mtime - time.time() > one_day:
            try:
                os.remove(path)
            except:
                logging.warn("Error deleteing: %s" % path)

@run_every_day
def update_search_data():
    logging.info('Updating Search Data')
    manage.update_search_data()

@run_every_day
def update_items():
    logging.info('Updating Items')
    manage.update_items()

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    log_path = os.path.join(settings.SITE_DIR, 'log', 'tasks.log')
    handler = logging.handlers.RotatingFileHandler(log_path, maxBytes=2**20)
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(handler)

if __name__ == '__main__':
    setup_logging()
    db_session = create_session(bind_to=db.engine)
    logging.info("Starting new log")
    tasks.run_tasks(db_session)
