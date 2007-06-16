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
import re
import shutil
import socket
import threading
import traceback
import Queue
from glob import glob

from django.conf.urls.defaults import patterns
from django.core import management 
action_mapping = management.DEFAULT_ACTION_MAPPING.copy()
original_action_mapping_keys = action_mapping.keys()
print_stuff = False

from channelguide import util

def syncdb(verbosity=None, interactive=None):
    "Synchronize the database with the current code."
    from channelguide import db
    db.syncdb()
syncdb.args = ''

FLUSH_EVERY_X_CHANNELS = 50
def all_channel_iterator(connection, task_description, *joins):
    """Helper method to iterate over all channels.  It will yield each channel
    in order.
    """

    from channelguide.guide.models import Channel

    query = Channel.query()
    if joins:
        query.join(*joins)
    if print_stuff:
        print "fetching channels..."
    channels = query.execute(connection)
    if print_stuff:
        pprinter = util.ProgressPrinter(task_description, len(channels))
        pprinter.print_status()
    for channel in channels:
        yield channel
        connection.commit()
        if print_stuff:
            pprinter.iteration_done()
    if print_stuff:
        pprinter.loop_done()

def get_channels():
    from channelguide import db
    from channelguide.guide.models import Channel
    connection = db.connect()
    try:
        return Channel.query().execute(connection)
    finally:
        connection.close()

def spawn_threads_for_channels(task_description, callback, thread_count):
    """Works with update_items and download_thumbnails to manage worker
    threads that update the individual channels.
    """

    from channelguide import db
    queue = Queue.Queue()
    for channel in get_channels():
        queue.put(channel)
    if print_stuff:
        pprinter = util.ProgressPrinter(task_description, queue.qsize())
        pprinter.print_status()
    class Worker(threading.Thread):
        def run(self):
            connection = db.connect()
            while True:
                try:
                    channel = queue.get(block=False)
                except Queue.Empty:
                    break
                callback(connection, channel)
                connection.commit()
                if print_stuff:
                    pprinter.iteration_done()
            connection.close()
    threads = [Worker() for x in range(thread_count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    if print_stuff:
        pprinter.loop_done()

def update_items(args=None):
    """Update the items for each channel."""
    from channelguide import db
    db.pool.max_connections = 20
    set_short_socket_timeout()

    def callback(connection, channel):
        channel.join('items').execute(connection)
        try:
            channel.update_items(connection)
        except:
            logging.warn("\nError updating items for %s\n\n%s\n" % 
                    (channel, traceback.format_exc()))
    spawn_threads_for_channels('updating items', callback, 4)
update_items.args = ''

def download_thumbnails(args=None):
    "update channel thumbnails."""

    from channelguide import db
    if args is None:
        args = []
    db.pool.max_connections = 20
    set_short_socket_timeout()
    redownload = (len(args) > 3 and args[3] in ('-r', '--redownload'))
    def callback(connection, channel):
        channel.join("items").execute(connection)
        try:
            channel.download_item_thumbnails(connection, redownload)
        except:
            logging.warn("\nerror updating thumbnails for %s\n\n%s\n" % 
                    (channel, traceback.format_exc()))
    spawn_threads_for_channels('updating thumbnails', callback, 4)
download_thumbnails.args = '[--redownload]'

def update_search_data(args=None):
    "Update the search data for each channel."
    from channelguide.guide import tables
    from channelguide import db
    connection = db.connect()
    connection.execute("""DELETE FROM cg_item_search_data
WHERE NOT EXISTS (SELECT * FROM cg_channel_item WHERE id=item_id)""")
    connection.execute("""DELETE FROM cg_channel_search_data
WHERE NOT EXISTS (SELECT * FROM cg_channel WHERE id=channel_id)""")

    iter = all_channel_iterator(connection, 'updating search data', 'items',
            'items.search_data')
    for channel in iter:
        channel.update_search_data(connection)
update_search_data.args = ''

def update_thumbnails(args):
    "Update channel thumbnails."""
    overwrite = False
    sizes = []
    for arg in args[2:]:
        if arg in ('-o', '--overwrite'):
            overwrite = True
        else:
            sizes.append(arg)
    if sizes == []:
        sizes = None
    from channelguide import db
    connection = db.connect()
    for channel in all_channel_iterator(connection, 'updating thumbnails',
            'items'):
        try:
            channel.update_thumbnails(connection, overwrite, sizes)
        except:
            logging.warn("\nError updating thumbnails for %s\n\n%s\n" % 
                    (channel, traceback.format_exc()))
update_thumbnails.args = '[size] [--overwrite]'

def fix_utf8_strings(args):
    "Update the search data for each channel."
    from channelguide import db
    connection = db.connect()
    for channel in all_channel_iterator(connection, 'fixing utf8 data', 'items'):
        channel.fix_utf8_strings(connection)

    from channelguide.guide import feedutil
    from channelguide.guide.models import Tag
    if print_stuff:
        print "fetching tags..."
    query = Tag.query()
    tags = query.execute(connection)
    if print_stuff:
        pprinter = util.ProgressPrinter('fixing tag utf8 data', len(tags))
        pprinter.print_status()
    for tag in tags:
        if feedutil.fix_utf8_strings(tag):
            tag.save(connection)
            connection.commit()
        if print_stuff:
            pprinter.iteration_done()
    if print_stuff:
        pprinter.loop_done()
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

def update_blog_posts(args=None):
    "Update posts from PCF's blog."
    from channelguide import db
    from channelguide.guide import blogtrack
    connection = db.connect()
    blogtrack.update_posts(connection)
update_blog_posts.args = ''

def make_icons(args):
    """Blend the channel icons for add and info against backgrounds, this is a
    workaround since IE doesn't support png alpha translucency.
    """
    from channelguide import icons
    icons.make_icons()
make_icons.args = ''

def remove_blank_space(args):
    """Remove blank space from the start/end of channel names and
    descriptions.
    """
    from channelguide import db
    connection = db.connect()
    for channel in all_channel_iterator(connection, "removing blank space"):
        change = False
        if channel.name.strip() != channel.name:
            change=True
            channel.name = channel.name.strip()
        if channel.description.strip() != channel.description:
            change=True
            channel.description = channel.description.strip()
        if change:
            channel.save(connection)
            connection.commit()
remove_blank_space.args = ''

def clear_cache(args):
    """Clear all cached pages.  """
    from channelguide import cache
    cache.clear_cache()
clear_cache.args = ''

def optimize_template_dir(source_dir, dest_dir):
    util.ensure_dir_exists(dest_dir)
    for file in os.listdir(source_dir):
        if not file.endswith(".html"):
            continue
        content = util.read_file(os.path.join(source_dir, file))
        optimized = "\n".join(line.strip() for line in content.split("\n"))
        util.write_file(os.path.join(dest_dir, file), optimized)

def optimize_templates(args):
    """Makes versions of the template files that are more space-efficient.
    Currently this means removing a bunch of whitepace.
    """
    from django.conf import settings
    from channelguide import util
    source_dir = settings.NORMAL_TEMPLATE_DIR
    dest_dir = settings.OPTIMIZED_TEMPLATE_DIR
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    optimize_template_dir(source_dir, dest_dir)
    optimize_template_dir(os.path.join(source_dir, 'guide'),
            os.path.join(dest_dir, 'guide'))

optimize_templates.args = ''

# Remove django default actions that we don't use.  Many of these probably
# would screw things up fairly bad.

for key in ['startproject', 'adminindex', 'createcachetable', 'install',
        'reset', 'sql', 'sqlall', 'sqlclear', 'sqlindexes', 'sqlinitialdata',
        'sqlreset', 'sqlsequencereset', 'validate']:
    try:
        del action_mapping[key]
    except KeyError:
        pass

action_mapping['syncdb'] = syncdb
action_mapping['download_thumbnails'] = download_thumbnails
action_mapping['update_search_data'] = update_search_data
action_mapping['fix_utf8_strings'] = fix_utf8_strings
action_mapping['update_thumbnails'] = update_thumbnails
action_mapping['update_items'] = update_items
action_mapping['drop_channel_data'] = drop_channel_data
action_mapping['drop_users'] = drop_users
action_mapping['update_blog_posts'] = update_blog_posts
action_mapping['make_icons'] = make_icons
action_mapping['remove_blank_space'] = remove_blank_space
action_mapping['clear_cache'] = clear_cache
action_mapping['optimize_templates'] = optimize_templates
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

def set_short_socket_timeout():
    socket.setdefaulttimeout(10) # makes update_items not take forever

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
                    format='%(levelname)s %(message)s',
                    stream=sys.stderr)
    print_stuff = True
    add_static_urls()
    try:
        action = sys.argv[1]
    except IndexError:
        action = None
    from channelguide import init
    if action == 'runserver':
        init.initialize()
    else:
        init.init_external_libraries()
    if (action not in original_action_mapping_keys and 
            action in action_mapping):
        func = action_mapping[action]
        func(sys.argv)
    else:
        management.execute_from_command_line(action_mapping, sys.argv)
