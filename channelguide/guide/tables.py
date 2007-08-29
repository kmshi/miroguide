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
    else:
        return _('Unknown')

# create the tables
category = Table('cg_category', 
        columns.Int('id', primary_key=True, auto_increment=True),
        columns.String('name', 200))
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
        columns.Boolean('channel_owner_emails', default=True))
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
        columns.String('short_description', 255),
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
        columns.Boolean('was_featured', default='0'),
        columns.DateTime('moderator_shared_at'),
        columns.Int('moderator_shared_by_id', fk=user.c.id, default=0),
        columns.DateTime('approved_at'),
        columns.String('cc_licence', 1, default='Z'),
        columns.Int('last_moderated_by_id', fk=user.c.id),
        columns.String('postal_code', 15))
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
        columns.String('type', 1),
        columns.String('title', 255),
        columns.String('body'),
        columns.DateTime('created_at', default=datetime.now))
channel_subscription = Table('cg_channel_subscription', 
        columns.Int('channel_id', fk=channel.c.id),
        columns.String('ip_address', 16),
        columns.DateTime('timestamp', default=datetime.now),
        columns.Int('ignore_for_recommendations'))
channel_recommendations = Table('cg_channel_recommendations',
        columns.Int('channel1_id', fk=channel.c.id),
        columns.Int('channel2_id', fk=channel.c.id),
        columns.Int('cosine')) # it's a float, but this should be okay
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

def make_subscription_count(name, timeline=None):
    sql = """\
SELECT COUNT(*)
FROM cg_channel_subscription
WHERE cg_channel_subscription.channel_id=#table#.id"""
    if timeline is not None:
        interval = "DATE_SUB(NOW(), INTERVAL 1 %s)" % timeline
        sql += " AND cg_channel_subscription.timestamp > %s" % interval
    channel.add_subquery_column(name, sql)

make_subscription_count('subscription_count')
make_subscription_count('subscription_count_today', 'DAY')
make_subscription_count('subscription_count_month', 'MONTH')

# set up relations
channel.many_to_many('categories', category, category_map, backref='channels')
channel.many_to_many('secondary_languages', language, secondary_language_map)
channel.many_to_many('tags', tag, tag_map, backref='channels')
channel.many_to_one('language', language)
channel.many_to_one('last_moderated_by', user,
        join_column=channel.c.last_moderated_by_id)
channel.one_to_many('items', item, backref='channel')
channel.one_to_many('notes', channel_note, backref='channel')
channel.one_to_one('search_data', channel_search_data, backref='channel')
item.one_to_one('search_data', item_search_data, backref='item')
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
