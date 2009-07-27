#!/usr/bin/env python
# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

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

import time
import logging
import shutil
import socket
import threading
import traceback
import Queue

from django.conf.urls.defaults import patterns
from django.core import management
try:
    managementUtility = management.ManagementUtility()
    commands = managementUtility.commands
except AttributeError:
    managementUtility = None
    commands = management.get_commands()

# Remove django default actions that we don't use.  Many of these probably
# would screw things up fairly bad.

for key in ['startproject', 'adminindex', 'createcachetable', 'install',
        'reset', 'sql', 'sqlall', 'sqlclear', 'sqlindexes', 'sqlinitialdata',
        'sqlreset', 'sqlsequencereset', 'validate']:
    try:
        del commands[key]
    except KeyError:
        pass
action_mapping = {}
print_stuff = False

from channelguide import util

def syncdb(verbosity=None, interactive=None):
    "Synchronize the database with the current code."
    from channelguide import db
    db.syncdb()
syncdb.args = ''

def get_channel_ids(approved=False):
    from channelguide import db
    from channelguide.guide.models import Channel
    connection = db.connect()
    if not approved:
        query = Channel.query()
    else:
        query = Channel.query_approved()
    try:
        return [c.id for c in query.execute(connection)]
    finally:
        connection.close()

def all_channel_iterator(connection, task_description, *joins, **kwargs):
    """Helper method to iterate over all channels.  It will yield each channel
    in order.
    """

    from channelguide.guide.models import Channel

    if print_stuff:
        print "fetching channels..."
    if 'approved' in kwargs:
        approved = kwargs.pop('approved')
    else:
        approved = False
    channel_ids = get_channel_ids(approved)
    if print_stuff:
        pprinter = util.ProgressPrinter(task_description, len(channel_ids))
        pprinter.print_status()
    for id in channel_ids:
        channel = Channel.get(connection, id, join=joins)
        yield channel
        connection.commit()
        if print_stuff:
            pprinter.iteration_done()
    if print_stuff:
        pprinter.loop_done()

def spawn_threads_for_channels(task_description, callback, thread_count):
    """Works with update_items and download_thumbnails to manage worker
    threads that update the individual channels.
    """

    from channelguide import db
    from channelguide.guide.models import Channel
    queue = Queue.Queue()
    for id in get_channel_ids():
        queue.put(id)
    if print_stuff:
        pprinter = util.ProgressPrinter(task_description, queue.qsize())
        pprinter.print_status()
    class Worker(threading.Thread):
        def run(self):
            connection = db.connect()
            while True:
                try:
                    id = queue.get(block=False)
                except Queue.Empty:
                    break
                channel = Channel.get(connection, id)
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
    from datetime import datetime
    db.pool.max_connections = 20
    set_short_socket_timeout()

    now = datetime.now()
    def callback(connection, channel):
        if channel.state == channel.SUSPENDED and now.weekday() != 6:
            # only check suspended feeds on Sunday
            return
        if not channel.is_approved() and channel.state != channel.SUSPENDED:
            # only check approved/suspended feeds
            return
        if channel.id % 24 != now.hour:
            # check channels throughout the day, some each hour
            return
        channel.join('items').execute(connection)
        try:
            start = time.time()
            channel.update_items(connection)
            length = time.time() - start
            if length > 6:
                logging.warn("Update too slow for %s: %f" % (channel.url,
                                                             length))
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
    redownload = (len(args) > 2 and args[2] in ('-r', '--redownload'))
    def callback(connection, channel):
        channel.join("items").execute(connection)
        try:
            channel.download_item_thumbnails(connection, redownload)
        except:
            logging.warn("\nerror updating thumbnails for %s\n\n%s\n" % 
                    (unicode(channel).encode('utf8'), traceback.format_exc()))
    spawn_threads_for_channels('updating thumbnails', callback, 4)
download_thumbnails.args = '[--redownload]'

def update_search_data(args=None):
    "Update the search data for each channel."
    from channelguide import db
    from channelguide.cache import client
    connection = db.connect()
    connection.execute("""DELETE FROM cg_item_search_data
WHERE NOT EXISTS (SELECT * FROM cg_channel_item WHERE id=item_id)""")
    connection.execute("""DELETE FROM cg_channel_search_data
WHERE NOT EXISTS (SELECT * FROM cg_channel WHERE id=channel_id)""")

    iter = all_channel_iterator(connection, 'updating search data', 'items',
            'items.search_data')
    for channel in iter:
        channel.update_search_data(connection)
    # refresh the search namespace
    client.set('search', time.time())
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
                    (unicode(channel).encode('utf8'), traceback.format_exc()))
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
    from channelguide.cache import client
    namespaces = args[2:]
    if not namespaces:
        namespaces = ['namespace', 'channel', 'search']
    for name in namespaces:
        client.set(name, time.time())
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
    source_dir = settings.NORMAL_TEMPLATE_DIR
    dest_dir = settings.OPTIMIZED_TEMPLATE_DIR
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    for path in ('', '/guide', '/feeds', '/donate'):
        optimize_template_dir(source_dir+path, dest_dir+path)
optimize_templates.args = ''

def remove_empty_tags(args=None):
    """Remove tags with 0 channels in them.  """
    from channelguide import db
    from channelguide.guide.models import Tag
    connection = db.connect()
    query = Tag.query().load('channel_count')
    query.having(channel_count=0)
    for tag in query.execute(connection):
        logging.info("Deleting empty tag: %s", tag.name)
        tag.delete(connection)
    connection.commit()

remove_empty_tags.args = ''

def block_old_unapproved_users(args=None):
    """
    Block users who have not approved their account after 3 days.
    """
    from channelguide import db
    from channelguide.guide.models import User
    from sqlhelper.sql.expression import Literal
    connection = db.connect()
    query = User.query()
    query.where(User.c.approved==0)
    query.where(User.c.blocked==0)
    query.where(User.c.created_at < Literal("DATE_SUB(NOW(), INTERVAL 3 DAY)"))
    for user in query.execute(connection):
        user.blocked = True
        append = 1
        name = user.username
        while True:
            try:
                user.save(connection)
            except:
                user.username = name + str(append)
                print 'trying', user.username
                append += 1
            else:
                break
    connection.commit()
block_old_unapproved_users.args = ''

def calculate_recommendations(args=None):
    """
    Calculate the item-item channel recomendations.
    """
    from channelguide import db
    from channelguide.guide import recommendations
    connection = db.connect()
    if args is not None and len(args) > 2 and args[2] == 'full':
        from channelguide.guide.models import Channel
        channels = Channel.query_approved().join('categories').execute(connection)
        recommendations.recalculate_similarity(channels, connection)
    else:
        recommendations.recalculate_similarity_recent(connection)
    connection.commit()
    connection.close()
calculate_recommendations.args = '[full]'
calculate_recommendations.args = ''

def refresh_popular_cache(args=None):
    """
    Finds the channels that have had subscriptions in the past 5 minutes
    and refreshes the number of subscriptions they've had in the past
    24 hours.  Then it finds the channels that have had subscriptions in the
    past hour and refreshes their monthly counts.
    """
    from channelguide import db, cache
    from channelguide.guide.models import Channel, Category
    class CacheClient:
        def get(self, key):
            return None
        def get_multi(self, keys):
            return {}
        def set(self, key, value, time=0):
            cache.client.set(key, value, time)
    connection = db.connect()
    queries = [
            (Channel.query_approved().join('stats').order_by('r_stats.subscription_count_today', desc=True).limit(7), 300),
           ]
    for cat in Category.query().execute(connection):
        query = Channel.query_approved().join('stats').join('categories').order_by('r_stats.subscription_count_month', desc=True).limit(2)
        query.joins['categories'].where(id=cat.id)
        queries.append((query, 300))

    cc = CacheClient()
    for query, cacheable_time in queries:
        query.cacheable = cc
        query.cacheable_time = cacheable_time
        query.execute(connection)
refresh_popular_cache.args = ''

def refresh_stats_table(args=None):
    """
    Refreshes the statistics table so that we can calculate the ranks of
    channels.  This also copies the recent subscriptions out of
    cg_channel_subscription_holding into the main table.
    """
    from channelguide import db
    conn = db.connect()
    copy_holding = """INSERT INTO cg_channel_subscription
    SELECT channel_id, timestamp, ip_address, ignore_for_recommendations
    FROM cg_channel_subscription_holding"""
    delete_holding = "DELETE FROM cg_channel_subscription_holding"
    conn.execute(copy_holding)
    conn.execute(delete_holding)
    conn.commit()
    delete_stats = "DELETE FROM cg_channel_generated_stats"
    insert_stats = """
    INSERT into cg_channel_generated_stats
    SELECT 
    cg_channel.id, 
      (
        SELECT
           COUNT(*)
        FROM 
           cg_channel_subscription
        WHERE 
           cg_channel_subscription.channel_id=cg_channel.id
       )
       AS cg_channel_subscription_count,
        (
        SELECT 
           COUNT(*)
        FROM 
           cg_channel_subscription
        WHERE 
           cg_channel_subscription.channel_id=cg_channel.id 
        AND 
           cg_channel_subscription.timestamp > DATE_SUB(NOW(), INTERVAL 1 MONTH)
      ) 
      AS cg_channel_subscription_count_month,
        (
        SELECT 
           COUNT(*)
        FROM 
           cg_channel_subscription
        WHERE 
           cg_channel_subscription.channel_id=cg_channel.id 
        AND 
           cg_channel_subscription.timestamp > DATE_SUB(NOW(), INTERVAL 1 DAY)
      ) 
      AS cg_channel_subscription_count_today
    FROM 
      cg_channel
    WHERE 
      cg_channel.state IN ('A', 'U')
    ORDER BY
      cg_channel_subscription_count_today
    DESC,
      cg_channel_subscription_count_month 
    DESC, 
      cg_channel_subscription_count
    DESC"""
    conn.execute(delete_stats)
    conn.execute(insert_stats)
    conn.commit()
    conn.close()
refresh_stats_table.args = ''

def update_new_channel_queue(args=None):
    """
    Update the cg_channel_last_approved table to include the next
    most-recently approved channel.
    """
    from channelguide import db
    conn = db.connect()
    new_channel = conn.execute('SELECT approved_at FROM cg_channel WHERE approved_at>(SELECT timestamp FROM cg_channel_last_approved) ORDER BY approved_at ASC LIMIT 1')
    if new_channel:
        conn.execute('UPDATE cg_channel_last_approved SET timestamp=%s',
                new_channel[0])
        conn.commit()
    conn.close()
update_new_channel_queue.args = ''

def shuffle_featured_channel_queue(args=None):
    """
    Shuffle the featured queue table.
    """
    from channelguide import db
    from channelguide.guide.models import FeaturedQueue, Channel
    conn = db.connect()
    FeaturedQueue.shuffle_queue(conn, Channel.APPROVED)
    FeaturedQueue.shuffle_queue(conn, Channel.AUDIO)
    conn.commit()
    conn.close()
shuffle_featured_channel_queue.args = ''


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
action_mapping['remove_empty_tags'] = remove_empty_tags
action_mapping['block_old_unapproved_users'] = block_old_unapproved_users
action_mapping['calculate_recommendations'] = calculate_recommendations
action_mapping['refresh_popular_cache'] = refresh_popular_cache
action_mapping['refresh_stats_table'] = refresh_stats_table
action_mapping['update_new_channel_queue'] = update_new_channel_queue
action_mapping['shuffle_featured_channel_queue'] = shuffle_featured_channel_queue

def add_static_urls():
    static_patterns = []
    base_dir = os.path.abspath(os.path.join(__file__, '..', '..', 'static'))
    for dir in ('css', 'media', 'images', 'js', 'movies', 'swf'):
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
    if action in action_mapping:
        func = action_mapping[action]
        func(sys.argv)
    else:
        if managementUtility:
            managementUtility.execute(sys.argv)
        else:
            from channelguide import settings
            management.execute_manager(settings)
