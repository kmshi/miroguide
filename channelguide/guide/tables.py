from sqlalchemy import (Column, String, DateTime, Table, Boolean, Integer,
        PassiveDefault, func, ForeignKey)
from channelguide import util

from channelguide import db

category = Table('cg_category', db.metadata,
        Column('id', Integer, nullable=False, primary_key=True),
        Column('name', String(200), nullable=False))

tag = Table('cg_tag', db.metadata,
        Column('id', Integer, nullable=False, primary_key=True),
        Column('name', String(200), nullable=False))

user = Table('user', db.metadata,
        Column('id', Integer, nullable=False, primary_key=True),
        Column('username', String(40), nullable=False, index=True,
            unique=True),
        Column('role', String(1), PassiveDefault('U'), nullable=False),
        Column('blocked', Boolean, PassiveDefault('0'), nullable=False),
        Column('approved', Boolean, PassiveDefault('0'), nullable=False),
        Column('show_explicit', Boolean, PassiveDefault('0'), nullable=False),
        Column('created_at', DateTime, nullable=False, default=func.now()),
        Column('updated_at', DateTime, nullable=False, default=func.now(),
            onupdate=func.now()),
        Column('fname', String(45), nullable=True),
        Column('lname', String(45), nullable=True),
        Column('email', String(100), nullable=True),
        Column('city', String(45), nullable=True),
        Column('state', String(20), nullable=True),
        Column('country', String(25), nullable=True),
        Column('zip', String(15), nullable=True),
        Column('im_username', String(35), nullable=True),
        Column('im_type', String(25), nullable=True),
        Column('hashed_password', String(40), nullable=False),
        Column('moderator_board_emails', Boolean(), PassiveDefault(1),
            nullable=False),
        Column('status_emails', Boolean(), PassiveDefault(1), nullable=False),
        Column('email_updates', Boolean, PassiveDefault('0'), nullable=False))

moderator_action = Table('cg_moderator_action', db.metadata,
        Column("id", Integer, primary_key=True, nullable=False),
        Column("user_id", Integer, ForeignKey('user.id'), nullable=False),
        Column("channel_id", Integer, ForeignKey('cg_channel.id'), nullable=False),
        Column("action", String(1), nullable=False),
        Column("timestamp", DateTime, nullable=False, default=func.now()))

language = Table('cg_channel_language', db.metadata,
        Column('id', Integer, nullable=False, primary_key=True),
        Column('name', String(40), nullable=False))

pcf_blog_post = Table('cg_pcf_blog_post', db.metadata,
        Column('id', Integer, nullable=False, primary_key=True),
        Column('title', String(255), nullable=False),
        Column('body', String(), nullable=False),
        Column('url', String(200), nullable=False),
        Column('position', Integer, nullable=False))

moderator_post = Table('cg_moderator_post', db.metadata,
        Column('id', Integer, nullable=False, primary_key=True),
        Column("user_id", Integer, ForeignKey('user.id'), nullable=False),
        Column('title', String(255), nullable=False),
        Column('body', String(), nullable=False),
        Column('created_at', DateTime(), default=func.now(), nullable=False))

channel = Table('cg_channel', db.metadata,
        Column('id', Integer, nullable=False, primary_key=True),
        Column('owner_id', Integer, ForeignKey('user.id'), nullable=False),
        Column('name', String(200), nullable=False),
        Column('url', String(200), nullable=False),
        Column('website_url', String(200), nullable=False),
        Column('short_description', String(255), nullable=False),
        Column("thumbnail_extension", String(8), nullable=True),
        Column('description', String, nullable=False),
        Column('hi_def', Boolean, PassiveDefault('0'), nullable=False),
        Column('primary_language_id', Integer, 
            ForeignKey('cg_channel_language.id'), nullable=False),
        Column('publisher', String(200), nullable=False),
        Column('state', String(1), PassiveDefault('N'), nullable=False),
        Column('modified', DateTime, PassiveDefault(None), nullable=True),
        Column('creation_time', DateTime, default=func.now()),
        Column('feed_modified', DateTime, PassiveDefault(None), nullable=True),
        Column('feed_etag', String(255), PassiveDefault(None), nullable=True),
        Column('featured', Boolean, PassiveDefault('0'), nullable=False),
        Column('featured_at', DateTime, PassiveDefault(None), nullable=True),
        Column('was_featured', Boolean, PassiveDefault('0'), nullable=False),
        Column('moderator_shared_at', DateTime, nullable=True),
        Column('approved_at', DateTime, nullable=True),
        Column('cc_licence', String(1), PassiveDefault('Z'), nullable=False))

channel_note = Table('cg_channel_note', db.metadata,
        Column('id', Integer, nullable=False, primary_key=True),
        Column('channel_id', Integer, ForeignKey('cg_channel.id'),
            nullable=False),
        Column("user_id", Integer, ForeignKey('user.id'), nullable=False),
        Column('type', String(1), nullable=False),
        Column('title', String(255), nullable=False),
        Column('body', String(), nullable=False),
        Column('created_at', DateTime(), default=func.now(), nullable=False))

channel_subscription = Table('cg_channel_subscription', db.metadata,
        Column('channel_id', Integer, ForeignKey('cg_channel.id'),
            nullable=False),
        Column('timestamp', DateTime, nullable=False, default=func.now()))

item = Table('cg_channel_item', db.metadata,
        Column('id', Integer, nullable=False, primary_key=True),
        Column('channel_id', Integer, ForeignKey('cg_channel.id'),
            nullable=False),
        Column("url", String(200), nullable=False),
        Column("name", String(200), nullable=False),
        Column("description", String(), nullable=False),
        Column("mime_type", String(50)),
        Column("thumbnail_url", String(255), nullable=True),
        Column("thumbnail_extension", String(8), nullable=True),
        Column("size", Integer),
        Column("guid", String(255), nullable=True),
        Column('date', DateTime()))

channel_search_data = Table('cg_channel_search_data', db.metadata,
        Column('channel_id', Integer, ForeignKey('cg_channel.id'),
            nullable=False, primary_key=True),
        Column('important_text', String(255), nullable=False),
        Column('text', String(), nullable=False))

item_search_data = Table('cg_item_search_data', db.metadata,
        Column('item_id', Integer, ForeignKey('cg_channel_item.id'), 
            nullable=False, primary_key=True),
        Column('important_text', String(255), nullable=False),
        Column('text', String(), nullable=False))

secondary_language_map = Table('cg_secondary_language_map', db.metadata,
        Column('channel_id', Integer, ForeignKey('cg_channel.id'),
            nullable=False, primary_key=True),
        Column('language_id', Integer, ForeignKey('cg_channel_language.id'),
            nullable=False, primary_key=True))

category_map = Table('cg_category_map', db.metadata,
        Column('channel_id', Integer, ForeignKey('cg_channel.id'), 
            nullable=False, primary_key=True),
        Column('category_id', Integer, ForeignKey('cg_category.id'), 
            nullable=False, primary_key=True))

tag_map = Table('cg_tag_map', db.metadata,
        Column('channel_id', Integer, ForeignKey('cg_channel.id'),
            nullable=False, primary_key=True),
        Column('user_id', Integer, ForeignKey('user.id'),
            nullable=False, primary_key=True),
        Column('tag_id', Integer, ForeignKey('cg_tag.id'),
            nullable=False, primary_key=True))

user_auth_token = Table('cg_user_auth_token', db.metadata,
        Column('user_id', Integer, ForeignKey('user.id'), primary_key=True,
            nullable=False),
        Column('token', String(255), nullable=False),
        Column('expires', DateTime(), nullable=False))
