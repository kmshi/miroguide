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
from sqlalchemy import create_session, eagerload, select
action_mapping = management.DEFAULT_ACTION_MAPPING.copy()
original_action_mapping_keys = action_mapping.keys()
print_stuff = False

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

def make_session():
    from channelguide import db
    connection = db.connect()
    return create_session(bind_to=connection)

FLUSH_EVERY_X_CHANNELS = 50
def all_channel_iterator(task_description):
    """Helper method to iterate over all channels.  It will yield each channel
    in order.
    """

    from channelguide.guide.models import Channel

    db_session = make_session()
    query = db_session.query(Channel).options(eagerload('items'))
    count = itertools.count()
    if print_stuff:
        print "fetching channels..."
    select = query.select()
    results = select.list()
    if print_stuff:
        pprinter = util.ProgressPrinter(task_description, select.count())
        pprinter.print_status()
    for channel in results:
        yield channel
        if count.next() % FLUSH_EVERY_X_CHANNELS == 0:
            db_session.flush()
        if print_stuff:
            pprinter.iteration_done()
    db_session.flush()
    if print_stuff:
        pprinter.loop_done()

def get_channel_ids():
    from channelguide import db
    from channelguide.guide import tables
    connection = db.connect()
    results = connection.execute(select([tables.channel.c.id]))
    rv = [row[0] for row in results]
    connection.close()
    return rv

def spawn_children(task_description, action_name, thread_count, extra_args=''):
    """Works with update_items and download_thumbnails to manage child processes
    that update the individual channels.
    """

    channel_ids = get_channel_ids()
    id_queue = Queue.Queue()
    for id in channel_ids:
        id_queue.put(id)
    if print_stuff:
        pprinter = util.ProgressPrinter(task_description, len(channel_ids))
        pprinter.print_status()
    class ChildSpawner(threading.Thread):
        def run(self):
            while True:
                try:
                    id = id_queue.get(block=False)
                except Queue.Empty:
                    break
                cmd = "python %s %s %d %s" % (__file__, action_name, id,
                        extra_args)
                os.system(cmd)
                if print_stuff:
                    pprinter.iteration_done()
    threads = [ChildSpawner() for x in range(thread_count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    if print_stuff:
        pprinter.loop_done()

def fetch_single_channel(db_session, args, arg_help):
    from channelguide.guide.models import Channel
    try:
        id = int(args[2])
    except (ValueError, IndexError):
        sys.stderr.write("syntax manage.py %s\n" % arg_help)
        sys.exit(1)
    else:
        return db_session.get(Channel, id)

def update_items(args=None):
    """Update the items for each channel."""
    spawn_children('updating items', "update_item", 4)
update_items.args = ''

def download_thumbnails(args=None):
    "update channel thumbnails."""
    if args is None:
        args = []
    extra_args = ' '.join(args[2:])
    spawn_children('updating thumbnails', "download_thumbnail", 4, extra_args)
download_thumbnails.args = '[--redownload]'

def update_item(args):
    """Update a single channel's item"""
    set_short_socket_timeout()
    db_session = make_session()
    channel = fetch_single_channel(db_session, args, update_item.args)
    if channel is not None:
        try:
            channel.update_items()
        except:
            logging.warn("\nError updating items for %s\n\n%s\n" % 
                    (channel, traceback.format_exc()))
        else:
            db_session.flush()
update_item.args = '<id>'

def download_thumbnail(args):
    "update channel thumbnails."""
    from channelguide import db

    set_short_socket_timeout()
    redownload = (len(args) > 3 and args[3] in ('-r', '--redownload'))
    db_session = make_session()
    channel = fetch_single_channel(db_session, args, download_thumbnail.args)
    if channel is not None:
        try:
            channel.download_item_thumbnails(redownload)
        except:
            logging.warn("\nerror updating thumbnails for %s\n\n%s\n" % 
                    (channel, traceback.format_exc()))
download_thumbnail.args = '<id> [--redownload]'

def update_search_data(args=None):
    "Update the search data for each channel."
    from channelguide.guide import tables
    from channelguide import db
    connection = db.connect()
    connection.execute("""DELETE FROM cg_item_search_data
WHERE NOT EXISTS (SELECT * FROM cg_channel_item WHERE id=item_id)""")
    connection.execute("""DELETE FROM cg_channel_search_data
WHERE NOT EXISTS (SELECT * FROM cg_channel WHERE id=channel_id)""")

    for channel in all_channel_iterator('updating search data'):
        channel.update_search_data()
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
    for channel in all_channel_iterator('updating thumbnails'):
        try:
            channel.update_thumbnails(overwrite, sizes)
        except:
            logging.warn("\nError updating thumbnails for %s\n\n%s\n" % 
                    (channel, traceback.format_exc()))
update_thumbnails.args = '[size] [--overwrite]'

def fix_utf8_strings(args):
    "Update the search data for each channel."
    for channel in all_channel_iterator('fixing utf8 data'):
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

def update_blog_posts(args=None):
    "Update posts from PCF's blog."
    from channelguide.guide import blogtrack
    db_session = make_session()
    blogtrack.update_posts(db_session)
    db_session.flush()
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
    for channel in all_channel_iterator("removing blank space"):
        if channel.name.strip() != channel.name:
            channel.name = channel.name.strip()
        if channel.description.strip() != channel.description:
            channel.description = channel.description.strip()
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
action_mapping['convert_old_data'] = convert_old_data
action_mapping['download_thumbnails'] = download_thumbnails
action_mapping['download_thumbnail'] = download_thumbnail
action_mapping['update_search_data'] = update_search_data
action_mapping['fix_utf8_strings'] = fix_utf8_strings
action_mapping['update_thumbnails'] = update_thumbnails
action_mapping['update_item'] = update_item
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
    if (len(sys.argv) > 1 and sys.argv[1] not in original_action_mapping_keys
            and sys.argv[1] in action_mapping):
        func = action_mapping[sys.argv[1]]
        func(sys.argv)
    else:
        management.execute_from_command_line(action_mapping, sys.argv)
