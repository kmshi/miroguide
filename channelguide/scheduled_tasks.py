import manage # must be 1st because it sets up sys.path

import fcntl
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
    if not os.path.exists(media_tmp_dir):
        logging.warn("%s doesn't exist" % media_tmp_dir)
        return
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

@run_every_day
def update_thumbnails():
    logging.info('downloading Thumbnails')
    manage.download_thumbnails()
    logging.info('Updating Thumbnails')
    manage.update_thumbnails([])

@run_every_hour
def update_blog_posts():
    logging.info('updating blog posts')
    manage.update_blog_posts()

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    log_path = os.path.join(settings.SITE_DIR, 'log', 'tasks.log')
    handler = logging.handlers.RotatingFileHandler(log_path, maxBytes=2**20)
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(handler)

if __name__ == '__main__':
    setup_logging()
    try:
        lock_path = os.path.join(settings.SITE_DIR, 'tasks.lock')
        lock_file = open(lock_path, 'w')
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        logging.warn("Could not obtain lock for %s.  Not starting." %
                lock_path)
    else:
        db_session = create_session(bind_to=db.engine)
        logging.info("--------- START ----------")
        tasks.run_tasks(db_session)
        logging.info("---------  END  ----------")
        lock_file.close()
        try:
            os.remove(lock_path)
        except IOError:
            pass
