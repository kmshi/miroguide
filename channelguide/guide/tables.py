# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from datetime import datetime

from django.utils.translation import gettext as _
from sqlhelper.sql import Select, Literal
from sqlhelper.orm import Table, columns

def name_for_state_code(state):
    if state == 'N':
        return _('New')
    elif state == 'A':
        return _('Approved')
    elif state == 'W':
        return _('Waiting')
    elif state == 'D':
        return _("Don't Know")
    elif state == 'R':
        return _('Rejected')
    elif state == 'S':
        return _('Suspended')
    elif state == 'U':
        return _('Audio')
    else:
        return _('Unknown')

# create the tables
category = Table('cg_category',
        columns.Int('id', primary_key=True, auto_increment=True),
        columns.String('name', 200),
        columns.Int('on_frontpage', default=1))
tag = Table('cg_tag',
        columns.Int('id', primary_key=True, auto_increment=True),
        columns.String('name', 200))
user = Table('user',
        columns.Int('id', primary_key=True, auto_increment=True),
        columns.String('username', 40),
        columns.String('role', 1, default='U'),
        columns.Boolean('blocked', default=False),
        columns.Boolean('approved', default=False),
        columns.Boolean('show_explicit', default=False),
        columns.DateTime('created_at', default=datetime.now),
        columns.DateTime('updated_at', default=datetime.now,
            onupdate=datetime.now),
        columns.String('fname', 45),
        columns.String('lname', 45),
        columns.String('email', 100),
        columns.String('city', 45),
        columns.String('state', 20),
        columns.String('country', 25),
        columns.String('zip', 15),
        columns.String('im_username', 35),
        columns.String('im_type', 25),
        columns.String('hashed_password', 40),
        columns.String('moderator_board_email', 1, default='S'),
        columns.Boolean('status_emails', default=True),
        columns.Boolean('email_updates', default=False),
        columns.Boolean('channel_owner_emails', default=True),
        columns.Int('age'),
        columns.String('gender', 1))
language = Table('cg_channel_language',
        columns.Int('id', primary_key=True, auto_increment=True),
        columns.String('name', 40))
pcf_blog_post = Table('cg_pcf_blog_post',
        columns.Int('id', primary_key=True, auto_increment=True),
        columns.String('title', 255),
        columns.String('body'),
        columns.String('url', 200),
        columns.Int('position'))
moderator_post = Table('cg_moderator_post',
        columns.Int('id', primary_key=True, auto_increment=True),
        columns.Int("user_id", fk=user.c.id),
        columns.String('title', 255),
        columns.String('body'),
        columns.DateTime('created_at', default=datetime.now))
channel = Table('cg_channel',
        columns.Int('id', primary_key=True, auto_increment=True),
        columns.Int('owner_id', fk=user.c.id),
        columns.String('name', 255),
        columns.String('url', 255),
        columns.String('website_url', 255),
        columns.String("thumbnail_extension", 8),
        columns.String('description'),
        columns.Boolean('hi_def', default='0'),
        columns.Int('primary_language_id', fk=language.c.id),
        columns.String('publisher', 255),
        columns.String('state', 1, default='N'),
        columns.DateTime('waiting_for_reply_date'),
        columns.DateTime('modified'),
        columns.DateTime('creation_time', default=datetime.now),
        columns.DateTime('feed_modified'),
        columns.String('feed_etag', 255),
        columns.Boolean('featured', default='0'),
        columns.DateTime('featured_at'),
        columns.Int('featured_by_id', fk=user.c.id),
        columns.Boolean('was_featured', default='0'),
        columns.DateTime('moderator_shared_at'),
        columns.Int('moderator_shared_by_id', fk=user.c.id),
        columns.DateTime('approved_at'),
        columns.String('license', 40, default=''),
        columns.Int('last_moderated_by_id', fk=user.c.id),
        columns.String('postal_code', 15),
        columns.Int('adult', default=0),
        columns.Int('archived', default=0))
moderator_action = Table('cg_moderator_action',
        columns.Int("id", primary_key=True, auto_increment=True),
        columns.Int("user_id", fk=user.c.id),
        columns.Int("channel_id", fk=channel.c.id),
        columns.String("action", 1),
        columns.DateTime("timestamp", default=datetime.now))
channel_note = Table('cg_channel_note',
        columns.Int('id', primary_key=True, auto_increment=True),
        columns.Int('channel_id', fk=channel.c.id),
        columns.Int("user_id", fk=user.c.id),
        columns.String('title', default=''),
        columns.String('body'),
        columns.Int('type', default=0),
        columns.DateTime('created_at', default=datetime.now))
channel_subscription = Table('cg_channel_subscription',
        columns.Int('channel_id', fk=channel.c.id),
        columns.String('ip_address', 16),
        columns.DateTime('timestamp', default=datetime.now),
        columns.Int('ignore_for_recommendations'))
channel_subscription_holding = Table('cg_channel_subscription_holding',
        *channel_subscription.columns.columns)
channel_recommendations = Table('cg_channel_recommendations',
        columns.Int('channel1_id', fk=channel.c.id),
        columns.Int('channel2_id', fk=channel.c.id),
        columns.Int('cosine')) # it's a float, but this should be okay
channel_rating = Table('cg_channel_rating',
        columns.Int('channel_id', fk=channel.c.id, primary_key=True),
        columns.Int('user_id', fk=user.c.id, primary_key=True),
        columns.Int('rating'),
        columns.DateTime('timestamp', default=datetime.now))
channel_review = Table('cg_channel_review',
        columns.Int('user_id', fk=user.c.id, primary_key=True),
        columns.Int('channel_id', fk=channel.c.id, primary_key=True),
        columns.String('review'),
        columns.DateTime('timestamp', default=datetime.now),
        columns.Int('is_public', default=True))
item = Table('cg_channel_item',
        columns.Int('id', primary_key=True, auto_increment=True),
        columns.Int('channel_id', fk=channel.c.id),
        columns.String("url", 255),
        columns.String("name", 255),
        columns.String("description"),
        columns.String("mime_type", 50),
        columns.String("thumbnail_url", 255),
        columns.String("thumbnail_extension", 8),
        columns.Int("size"),
        columns.String("guid", 255),
        columns.DateTime('date'))
channel_search_data = Table('cg_channel_search_data',
        columns.Int('channel_id', fk=channel.c.id, primary_key=True),
        columns.String('important_text', 255),
        columns.String('text'))
item_search_data = Table('cg_item_search_data',
        columns.Int('item_id', fk=item.c.id, primary_key=True),
        columns.String('important_text', 255),
        columns.String('text'))
secondary_language_map = Table('cg_secondary_language_map',
        columns.Int('channel_id', fk=channel.c.id, primary_key=True),
        columns.Int('language_id', fk=language.c.id, primary_key=True))
category_map = Table('cg_category_map',
        columns.Int('channel_id', fk=channel.c.id, primary_key=True),
        columns.Int('category_id', fk=category.c.id, primary_key=True))
tag_map = Table('cg_tag_map',
        columns.Int('channel_id', fk=channel.c.id, primary_key=True),
        columns.Int('user_id', fk=user.c.id, primary_key=True),
        columns.Int('tag_id', fk=tag.c.id, primary_key=True))
user_auth_token = Table('cg_user_auth_token',
        columns.Int('user_id', fk=user.c.id, primary_key=True),
        columns.String('token', 255),
        columns.DateTime('expires'))
featured_queue = Table('cg_channel_featured_queue',
        columns.Int('channel_id', fk=channel.c.id, primary_key=True),
        columns.Int('state', default=0),
        columns.Int('featured_by_id', fk=user.c.id),
        columns.DateTime('featured_at', default=datetime.now))
featured_email = Table('cg_channel_featured_email',
        columns.Int('sender_id', fk=user.c.id),
        columns.Int('channel_id', fk=channel.c.id, primary_key=True),
        columns.String('email', 100),
        columns.String('title', 100),
        columns.String('body'),
        columns.DateTime('timestamp', primary_key=True, default=datetime.now))
generated_ratings = Table('cg_channel_generated_ratings',
        columns.Int('channel_id', fk=channel.c.id, primary_key=True),
        columns.Int('average'),
        columns.Int('count'),
        columns.Int('total'))
api_key = Table('cg_api_key',
    columns.String('api_key', 40, primary_key=True),
    columns.Int('owner_id', fk=user.c.id),
    columns.Int('active'),
    columns.String('description'),
    columns.DateTime('created_at', default=datetime.now))
watched_videos = Table('cg_watched_videos',
                       columns.Int('type', primary_key=True),
                       columns.Int('id', primary_key=True),
                       columns.Int('count', default=0))
cobranding = Table('cg_cobranding',
        columns.Int('name', fk=user.c.username, primary_key=True),
        columns.String('html_title', 100),
        columns.String('page_title', 100),
        columns.String('url', 100),
        columns.String('icon_url', 100),
        columns.String('favicon_url', 100),
        columns.String('css_url', 100),
        columns.String('description'),
        columns.String('link1_url', 100),
        columns.String('link1_text', 100),
        columns.String('link2_url', 100),
        columns.String('link2_text', 100),
        columns.String('link3_url', 100),
        columns.String('link3_text', 100))
# set up count subquery columns.  These are a little more complex than the
# other columns, so they are separated out
category.add_subquery_column('channel_count', """\
SELECT COUNT(*)
FROM cg_channel
JOIN cg_category_map ON cg_channel.id=cg_category_map.channel_id
WHERE cg_channel.state='A' AND
      cg_category_map.category_id=#table#.id""")

tag.add_subquery_column('user_count', """\
SELECT COUNT(DISTINCT(cg_tag_map.user_id))
FROM cg_tag_map
WHERE cg_tag_map.tag_id=#table#.id""")

tag.add_subquery_column('channel_count', """
SELECT COUNT(DISTINCT(cg_channel.id)) FROM cg_channel
JOIN cg_tag_map ON cg_tag_map.channel_id=cg_channel.id
WHERE cg_channel.state='A' AND cg_tag_map.tag_id=#table#.id""")

language.add_subquery_column('channel_count', """
SELECT COUNT(DISTINCT(cg_channel.id))
FROM cg_channel
LEFT JOIN cg_secondary_language_map ON cg_secondary_language_map.channel_id=cg_channel.id
WHERE cg_channel.STATE='A' AND
       (cg_channel.primary_language_id=#table#.id OR
       cg_secondary_language_map.language_id=#table#.id)""")

user.add_subquery_column('moderator_action_count', """\
SELECT COUNT(DISTINCT(cg_moderator_action.channel_id))
FROM cg_moderator_action
WHERE cg_moderator_action.user_id=#table#.id""")

channel.add_subquery_column('item_count', """\
SELECT COUNT(*)
FROM cg_channel_item
WHERE cg_channel_item.channel_id=#table#.id""")
'''
channel.add_subquery_column('count_rating', """\
SELECT COUNT(rating)
FROM cg_channel_rating JOIN user ON user.id=cg_channel_rating.user_id
WHERE cg_channel_rating.channel_id=#table#.id AND user.approved=1""")

channel.add_subquery_column('average_rating', """\
SELECT IFNULL(ROUND(AVG(rating), 1), 0)
FROM cg_channel_rating JOIN user ON user.id=cg_channel_rating.user_id
WHERE cg_channel_rating.channel_id=#table#.id AND user.approved=1""")
'''
def make_subscription_count(name, timeline=None):
    if timeline is None:
        column = 'subscription_count_total'
    elif timeline == 'DAY':
        column = 'subscription_count_today'
    else:
        column = 'subscription_count_month'
    sql = """SELECT %s FROM cg_channel_generated_stats WHERE
channel_id=#table#.id""" % column
#    if 1:#else:
#        sql = """\
        #SELECT COUNT(*)
#FROM cg_channel_subscription
#WHERE cg_channel_subscription.channel_id=#table#.id"""
#        if timeline is not None:
#            interval = "DATE_SUB(NOW(), INTERVAL 1 %s)" % timeline
#            sql += " AND cg_channel_subscription.timestamp > %s" % interval
    channel.add_subquery_column(name, sql)
    rank_names = ['subscription_count_total']
    if timeline != None:
        rank_names.append('subscription_count_month')
    if timeline == 'DAY':
        rank_names.append('subscription_count_today')
    rank_names.reverse()
    rank_where = ' AND '.join(["%s > (SELECT %s FROM cg_channel_generated_stats WHERE channel_id=#table#.id)" % (n, n) for n in rank_names])
    rank_sql = "SELECT CONCAT(1+COUNT(*),'/',(SELECT COUNT(*) FROM cg_channel_generated_stats)) FROM cg_channel_generated_stats WHERE %s" % rank_where
    channel.add_subquery_column(name+"_rank", rank_sql)

make_subscription_count('subscription_count')
make_subscription_count('subscription_count_today', 'DAY')
make_subscription_count('subscription_count_month', 'MONTH')

featured_queue.add_subquery_column('last_time', """\
COALESCE(
    (SELECT featured_at from cg_channel_featured_queue AS q2 WHERE q2.state!=0
    AND q2.featured_by_id=#table#.featured_by_id
     ORDER BY featured_at DESC LIMIT 1), 0)""")

# set up relations
channel.many_to_many('categories', category, category_map, backref='channels')
channel.many_to_many('secondary_languages', language, secondary_language_map)
channel.many_to_many('tags', tag, tag_map, backref='channels')
channel.many_to_one('language', language)
channel.many_to_one('last_moderated_by', user,
        join_column=channel.c.last_moderated_by_id)
channel.many_to_one('featured_by', user,
        join_column=channel.c.featured_by_id)
channel.one_to_many('items', item, backref='channel')
channel.one_to_many('notes', channel_note, backref='channel')
channel.one_to_one('search_data', channel_search_data, backref='channel')
channel.one_to_one('rating', generated_ratings, backref='channel')
item.one_to_one('search_data', item_search_data, backref='item')
item.many_to_one('channel', channel, backref='item')
category_map.many_to_one('category', category, backref='category_maps')
category_map.many_to_one('channel', channel, backref='category_maps')
tag_map.many_to_one('channel', channel, backref='tag_maps')
tag_map.many_to_one('tag', tag)
tag_map.many_to_one('user', user, backref='tag_maps')
user.one_to_many('channels', channel, backref='owner',
        join_column=channel.c.owner_id)
user.one_to_many('moderator_posts', moderator_post, backref='user')
user.one_to_many('notes', channel_note, backref='user')
user.one_to_one('auth_token', user_auth_token, backref='user')
moderator_action.many_to_one('user', user, backref='moderator_actions')
moderator_action.many_to_one('channel', channel, backref='moderator_actions')
api_key.many_to_one('owner', user)
channel_rating.many_to_one('user', user, backref='channel_rating')
channel_rating.many_to_one('channel', channel, backref='channel_rating')
featured_queue.one_to_one('channel', channel, backref='featured_queue')
featured_queue.many_to_one('featured_by', user)
featured_email.many_to_one('sender', user, backref='featured_email')
