#!/usr/bin/env python
"""manage.py

Channelguide management system.  This has been modified a good deal from the
stock django version.  In particular the database functions, testing functions
have been changed.
"""
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
try:
    sys.path.remove(os.path.abspath(os.path.dirname(__file__)))
except ValueError:
    pass
os.environ['DJANGO_SETTINGS_MODULE'] = 'channelguide.settings'

import itertools
import logging
import threading
import traceback
import Queue

from django.conf.urls.defaults import patterns
from django.core import management 
from sqlalchemy import create_session, eagerload, desc, exists, not_
action_mapping = management.DEFAULT_ACTION_MAPPING.copy()
original_action_mapping_keys = action_mapping.keys()

from channelguide import util

def syncdb(verbosity=None, interactive=None):
    "Synchronize the database with the current code."
    from channelguide import db
    db.syncdb()
syncdb.args = ''

def convert_old_data(args):
    "Convert databse data from videobomb and the old channelguide."
    from channelguide.util.convert_old_data import convert_old_data
    if len(args) != 4:
        sys.stderr.write("usage manage.py convert_old_data "
                '<channelguide db dump> <videobomb db dump>\n')
        sys.exit(1)
    convert_old_data(args[2], args[3])
convert_old_data.args = '<videobomb db name> <channelguide db name>'

def all_channel_iterator(progress_string, flush_every_x_channels):
    """Helper method to iterate over all channels.  It will yield each channel
    in order, and print progress info."""

    from channelguide import db
    from channelguide.guide.models import Channel

    db_session = create_session(bind_to=db.engine)
    query = db_session.query(Channel).options(eagerload('items'))
    pprinter = util.ProgressPrinter(progress_string, query.count())
    count = itertools.count()
    print "fetching channels..."
    results = query.select()
    for channel in results:
        yield channel
        if count.next() % flush_every_x_channels == 0:
            db_session.flush()
        pprinter.iteration_done()
    pprinter.loop_done()
    db_session.flush()

def all_channel_iterator_threaded(progress_string, flush_every_x_channels,
        worker_callback, thread_count=10):
    """Helper method to iterate over all channels.  It works like
    all_channel_iterator, but instead of yielding channels it creates
    a group of threads.  worker_callback is called for each channel in the DB.
    """
    from channelguide import db
    from channelguide.guide.models import Channel

    connection = db.connect()
    db_session = create_session(bind_to=connection)
    query = db_session.query(Channel).options(eagerload('items'))
    channel_queue = Queue.Queue()
    print "fetching channels..."
    for channel in query.select():
        channel_queue.put(channel.id)
    pprinter = util.ProgressPrinter(progress_string, query.count())
    connection.close()
    class WorkerThread(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            self.db_session = create_session(bind_to=db.engine)
        def run(self):
            count = itertools.count()
            while True:
                try:
                    id = channel_queue.get(block=False)
                except Queue.Empty:
                    break
                else:
                    channel = self.db_session.get(Channel, id)
                    worker_callback(channel)
                    if count.next() % flush_every_x_channels == 0:
                        self.db_session.flush()
                        self.db_session.clear()
                    pprinter.iteration_done()
    workers = [WorkerThread() for i in range(thread_count)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    pprinter.loop_done()

def update_thumbnails(args):
    "Update channel thumbnails."""
    redownload = overwrite = False
    sizes = []
    for arg in args[2:]:
        if arg in ('-o', '--overwrite'):
            overwrite = True
        elif arg in ('-r', '--redownload'):
            redownload = True
        else:
            sizes.append(arg)
    if sizes == []:
        sizes = None
    def callback(channel):
        try:
            channel.update_thumbnails(overwrite, redownload, sizes)
        except:
            print "\nError updating thumbnails for %s\n\n%s\n" % \
                    (channel, traceback.format_exc())
    all_channel_iterator_threaded("updating thumbnails", 40, callback)
update_thumbnails.args = '[size] [--overwrite]'

def update_items(args):
    """Update the items for each channel."""
    def callback(channel):
        try:
            channel.update_items()
        except:
            print "\nError updating items for %s\n\n%s\n" % \
                    (channel, traceback.format_exc())
    all_channel_iterator_threaded("updating items", 40, callback)
update_items.args = ''


def update_search_data(args):
    "Update the search data for each channel."
    from channelguide.guide import tables
    from channelguide import db
    connection = db.connect()
    connection.execute("""DELETE FROM cg_item_search_data
WHERE NOT EXISTS (SELECT * FROM cg_channel_item WHERE id=item_id)""")
    connection.execute("""DELETE FROM cg_channel_search_data
WHERE NOT EXISTS (SELECT * FROM cg_channel WHERE id=channel_id)""")

    for channel in all_channel_iterator("updating search data", 10):
        channel.update_search_data()
update_search_data.args = ''

def fix_utf8_strings(args):
    "Update the search data for each channel."
    for channel in all_channel_iterator("fixing utf-8 data", 100):
        channel.fix_utf8_strings()
fix_utf8_strings.args = ''

def drop_channel_data(args):
    "Drop all channel, category, tags and language data from the database."
    from channelguide import db
    conn = db.connect()
    conn.execute("DELETE FROM cg_channel")
    conn.execute("DELETE FROM cg_category")
    conn.execute("DELETE FROM cg_tag")
    conn.execute("DELETE FROM cg_channel_language")
drop_channel_data.args = ''

def drop_users(args):
    "Drop all users in the database"
    from channelguide import db
    conn = db.connect()
    conn.execute("DELETE FROM user")
drop_users.args = ''

def update_blog_posts(args):
    "Update posts from PCF's blog."
    from channelguide import db
    from channelguide import blogtrack
    db_session = create_session(bind_to=db.engine)
    blogtrack.update_posts(db_session)
    db_session.flush()
update_blog_posts.args = ''

# Remove django default actions that we don't use.  Many of these probably
# would screw things up fairly bad.
del action_mapping['startproject']
del action_mapping['adminindex']
del action_mapping['createcachetable']
del action_mapping['install']
del action_mapping['reset']
del action_mapping['sql']
del action_mapping['sqlall']
del action_mapping['sqlclear']
del action_mapping['sqlindexes']
del action_mapping['sqlinitialdata']
del action_mapping['sqlreset']
del action_mapping['sqlsequencereset']
del action_mapping['validate']

action_mapping['syncdb'] = syncdb
action_mapping['convert_old_data'] = convert_old_data
action_mapping['update_thumbnails'] = update_thumbnails
action_mapping['update_search_data'] = update_search_data
action_mapping['fix_utf8_strings'] = fix_utf8_strings
action_mapping['update_items'] = update_items
action_mapping['drop_channel_data'] = drop_channel_data
action_mapping['drop_users'] = drop_users
action_mapping['update_blog_posts'] = update_blog_posts
del action_mapping['test']

def add_static_urls():
    static_patterns = []
    base_dir = os.path.abspath(os.path.join(__file__, '..', '..', 'static'))
    for dir in ('css', 'media', 'images', 'js'):
        static_patterns.append((r'^%s/(?P<path>.*)$' % dir, 
            'django.views.static.serve',
            {'document_root': os.path.join(base_dir, dir)}))
    from channelguide.guide.urls import root
    root.urlpatterns.extend(patterns ('', *static_patterns))

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
                    format='%(levelname)s %(message)s',
                    stream=sys.stderr)
    add_static_urls()
    if (len(sys.argv) > 1 and sys.argv[1] not in original_action_mapping_keys
            and sys.argv[1] in action_mapping):
        func = action_mapping[sys.argv[1]]
        func(sys.argv)
    else:
        management.execute_from_command_line(action_mapping, sys.argv)
