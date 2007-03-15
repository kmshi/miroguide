from datetime import datetime
from urlparse import urljoin
from glob import glob
import itertools
import logging
import traceback
import urllib2

from django.conf import settings
from django.utils.translation import ngettext
from sqlalchemy import (mapper, relation, backref, MapperExtension, and_,
        object_session, class_mapper, select, text, join, desc, String, func)

from channelguide import util
from channelguide.auth.models import User
from channelguide.auth import tables as auth_tables
from channelguide.languages.models import Language
from channelguide.lib import feedparser
from channelguide.util import feedutil
from thumbnail import Thumbnailable
import tables as t

class FeedparserEntryError(ValueError):
    """Error parsing a feedparser entry object"""
    pass

class Label(object):
    """Label is the base class for both Category and Tag."""
    def __init__(self, name=None):
        self.name = name

    def link(self):
        return util.make_link(self.get_absolute_url(), str(self))

    def __str__(self):
        return self.name

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.name)

class Category(Label):
    """Categories are created by the admins and assigned to a channel by that
    channel's submitter.
    """
    def get_absolute_url(self):
        return util.make_absolute_url('categories/%d' % self.id)

class Tag(Label):
    """Tags are user created labels.  Any string of text can be a tag and any
    user can tag any channel.
    """
    def get_absolute_url(self):
        return util.make_absolute_url('tags/%d' % self.id)

class TagMap(object):
    def __init__(self, channel, user, tag):
        self.channel_id = channel.id
        self.user_id = user.id
        self.tag_id = tag.id

class FullTextSearchable:
    """Mixin class that helps with full text search capabilities."""

    def refresh_search_data(self):
        session = object_session(self)
        search_data = session.get(self.search_data_class, self.id)
        if search_data is None:
            search_data = self.search_data_class(self.id)
        self.fill_search_data(search_data)
        util.save_if_new(session, search_data)

    def get_search_data(self):
        values = [getattr(self, attr) for attr in self.search_attributes]
        return ' '.join(values)

    def get_search_data_important(self):
        attr_list = self.search_attributes_important
        values = [getattr(self, attr) for attr in attr_list]
        return ' '.join(values)

    def fill_search_data(self, search_data):
        search_data.text = self.get_search_data()
        search_data.important_text = self.get_search_data_important()

    @staticmethod
    def _search_where_clause():
        return text("MATCH(important_text, text) AGAINST "
                    "(:boolean_query IN BOOLEAN MODE)")

    @classmethod
    def _build_search_select(cls, columns, limit=None):
        score = text("(MATCH(important_text) AGAINST (:search_query)) * 5"
                "+ (MATCH(important_text, text) AGAINST (:search_query)) "
                "AS score")
        s = select(columns + [score], cls._search_where_clause(),
                limit=limit)
        s.order_by(desc('score'))
        return s

    @staticmethod
    def _search_execute_params(terms):
        return {
            'search_query': ' '.join(terms),
            'boolean_query': ' '.join(['+%s*' % t for t in terms]),
        }

    @classmethod
    def _execute_search(cls, connection, select, terms):
        return connection.execute(select, **cls._search_execute_params(terms))

    @classmethod
    def count_search_results(cls, connection, terms):
        table = class_mapper(cls.search_data_class).local_table
        s = select([func.count('*')], cls._search_where_clause(),
                from_obj=[table])
        results = connection.execute(s, **cls._search_execute_params(terms))
        return list(results)[0][0]

    @classmethod
    def search(cls, db_session, terms, limit=None):
        table = class_mapper(cls).local_table
        sort_table = class_mapper(cls.search_data_class).local_table

        select = cls._build_search_select([table], limit)
        select.append_from(join(sort_table, table))

        q = db_session.query(cls)
        connection = db_session.connection(class_mapper(cls))
        return q.instances(cls._execute_search(connection, select, terms))

    @classmethod
    def id_search(cls, connection, terms, limit=None):
        id = class_mapper(cls.search_data_class).primary_key
        select = cls._build_search_select(list(id), limit)
        results = cls._execute_search(connection, select, terms)
        if len(id) == 1:
            return [row[0] for row in results]
        else:
            # this should cover multi-column primary keys
            return [row[:len(id)] for row in results]

class UTF8Fixable:
    """Mixin class that fixes invalid utf-8 data."""


    def get_string_columns(self):
        return [c for c in self.c if isinstance(c.type, String)]

    def fix_utf8_strings(self):
        # cache string columns for fast access
        try:
            columns = self.__class__._string_columns
        except AttributeError:
            columns = self.get_string_columns()
            self.__class__._string_columns = columns
        for c in columns:
            org = getattr(self, c.name)
            if org is None:
                continue
            fixed = feedutil.to_utf8(org)
            if org != fixed:
                setattr(self, c.name, fixed)

class ChannelSearchData(object):
    def __init__(self, channel_id):
        self.channel_id = channel_id
mapper(ChannelSearchData, t.channel_search_data)

class ItemSearchData(object):
    def __init__(self, item_id):
        self.item_id = item_id
mapper(ItemSearchData, t.item_search_data)

class Channel(Thumbnailable, FullTextSearchable, UTF8Fixable):
    """An RSS feed containing videos for use in Democracy."""
    NEW = 'N'
    WAITING = 'W'
    DONT_KNOW = 'D'
    REJECTED = 'R'
    APPROVED = 'A'

    cc_licence_codes = {
     'Z': 'Not CC Licensed',
     'X': 'Mixed CC Licensing',
     'A': 'Attribution',
     'B': 'Attribution-NoDerivs',
     'C': 'Attribution-NonCommercial-NoDerivs',
     'D': 'Attribution-NonCommercial',
     'E': 'Attribution-NonCommercial-ShareAlike',
     'F': 'Attribution-ShareAlike',
    }

    THUMBNAIL_DIR = 'thumbnails'
    THUMBNAIL_SIZES = [
            (60, 40),
            (120, 80),
            (165, 110),
            (252, 169),
            (370, 247),
    ]

    search_data_class = ChannelSearchData
    search_attributes_important = ('name',)
    def get_search_data(self):
        simple_attrs = ('short_description', 'description', 'url',
                'website_url', 'publisher')
        values = [getattr(self, attr) for attr in simple_attrs]
        values.append(self.language.name)
        for attr in ('tags', 'categories', 'secondary_languages'):
            for obj in getattr(self, attr):
                values.append(obj.name)
        return ' '.join(values)

    def __str__(self):
        return "%s (%s)" % (self.name, self.url)

    def get_absolute_url(self):
        return util.make_absolute_url('channels/%d' % self.id)

    def get_subscription_url(self):
        return util.make_absolute_url('channels/subscribe/%d' % self.id)

    def is_approved(self):
        return self.state == self.APPROVED

    def add_tag(self, user, tag_name):
        """Add a tag to this channel."""
        db_session = object_session(self)
        existing = db_session.query(Tag).select_by(name=tag_name).list()
        if len(existing) > 0:
            tag = existing[0]
        else:
            tag = Tag(tag_name)
            db_session.save(tag)
            db_session.flush([tag])
        if not db_session.get(TagMap, (self.id, user.id, tag.id)):
            self.tag_maps.append(TagMap(self, user, tag))

    def add_tags(self, user, tags):
        """Tag this channel with a list of tags."""
        for tag in tags:
            self.add_tag(user, tag)

    def get_subscription_str(self):
        return ngettext('%(count)d subscriber', 
                '%(count)d subscribers', self.subscriptions.count) % {
                'count': self.subscriptions.count
        }

    def get_episodes_str(self):
        count = self.item_info.count
        return ngettext('%(count)d episode', '%(count)d episodes', count) % {
                'count': count
        }

    def add_subscription(self, connection, timestamp=None):
        if self.id is None:
            msg = "Channel must be saved before add_subscription() is called"
            raise ValueError(msg)
        values = {'channel_id': self.id}
        if timestamp is not None:
            values['timestamp'] = timestamp
        connection.execute(t.channel_subscription.insert(), values)

    def refresh_thumbnails(self, overwrite=False, sizes=None):
        """Recreate the thumbnails using the original data."""

        if self.thumbnail_extension is None:
            pattern = self.thumb_path('original')
            pattern = pattern.replace("missing.png", "%d.*" % self.id)
            matches = glob(pattern)
            if matches:
                data = util.read_file(matches[0])
                self.thumbnail_extension = util.get_image_extension(data)

        Thumbnailable.refresh_thumbnails(self, overwrite, sizes)
        for item in self.items:
            item.refresh_thumbnails(overwrite, sizes)

    def refresh_search_data(self):
        FullTextSearchable.refresh_search_data(self)
        for item in self.items:
            item.refresh_search_data()

    def fix_utf8_strings(self):
        UTF8Fixable.fix_utf8_strings(self)
        for item in self.items:
            item.fix_utf8_strings()

    def update_items(self, db_session, feedparser_input=None):
        try:
            if feedparser_input is None:
                parsed = feedparser.parse(self.url)
            else:
                parsed = feedparser.parse(feedparser_input)
        except:
            print "WARNING: ERROR parsing %s" % self.url
            traceback.print_exc()
        else:
            items = []
            for entry in parsed.entries:
                if feedutil.get_first_video_enclosure(entry) is None:
                    continue
                try:
                    items.append(Item.from_feedparser_entry(entry))
                except ValueError, e:
                    logging.warn("Error converting feedparser entry: %s (%s)" 
                            % (e, self))
            self._replace_items(db_session, items)
            db_session.flush(self.items)
            for item in self.items:
                item.download_thumbnail()
            db_session.flush(self.items)

    def _replace_items(self, db_session, items):
        """Replace the items currently in the channel with a new list of
        items."""

        for i in self.items:
            db_session.delete(i)
        for i in items:
            self.items.append(i)
            db_session.save(i)

    def _thumb_html(self, width, height):
        thumb_url = self.thumb_url(width, height)
        img = '<img src="%s" alt="%s">' % (thumb_url, self.name)
        return util.make_link(self.get_absolute_url(), img)

    def thumb_60_40(self): return self._thumb_html(60, 40)
    def thumb_120_80(self): return self._thumb_html(120, 80)
    def thumb_165_110(self): return self._thumb_html(165, 110)
    def thumb_252_169(self): return self._thumb_html(252, 169)
    def thumb_370_247(self): return self._thumb_html(370, 247)

    def name_as_link(self):
        return util.make_link(self.get_absolute_url(), self.name)

    def change_state(self, newstate):
        self.state = newstate
        if newstate == self.APPROVED:
            self.approved_at = datetime.now()
        else:
            self.approved_at = None

    def feature(self, connection):
        self.featured = True
        self.featured_at = datetime.now()

    def toggle_moderator_share(self):
        if self.moderator_shared_at is None:
            self.moderator_shared_at = datetime.now()
        else:
            self.moderator_shared_at = None

    @staticmethod
    def search_items(db_session, query, limit=None):
        connection = db_session.connection(channel_mapper)
        item_ids = Item.id_search(connection, query)
        q = db_session.query(Channel)
        select = q.select(q.join_to('items') & Item.c.id.in_(*item_ids))
        if limit is not None:
            select.limit(limit)
        return select.list()

class Item(Thumbnailable, FullTextSearchable, UTF8Fixable):
    THUMBNAIL_DIR = 'item-thumbnails'
    THUMBNAIL_SIZES = [
            (108, 81),
    ]

    search_data_class = ItemSearchData
    search_attributes = ('description', 'url')
    search_attributes_important = ('name', )

    def thumb(self):
        url = self.thumb_url(108, 81)
        return '<img width="108" height="81" src="%s" alt="%s">' % (url, self.name)

    def download_thumbnail(self):
        if self.thumbnail_url is not None:
            try:
                image_data = urllib2.urlopen(self.thumbnail_url).read()
            except urllib2.URLError, ValueError:
                pass
            else:
                self.save_thumbnail(image_data)

    @staticmethod
    def from_feedparser_entry(entry):
        enclosure = feedutil.get_first_video_enclosure(entry)
        if enclosure is None:
            raise FeedparserEntryError("No video enclosure")
        rv = Item()
        try:
            rv.name = feedutil.to_utf8(entry['title'])
            rv.url = feedutil.to_utf8(enclosure['url'])
            try:
                rv.desciption = feedutil.to_utf8(enclosure['text'])
            except KeyError:
                try:
                    rv.description = feedutil.to_utf8(entry.description)
                except AttributeError:
                    # this is a weird hack, for some reason if we use
                    # entry['description'] and it isn't present a feedparser
                    # raises a TypeError instead of a KeyError
                    raise KeyError('description')
            rv.mime_type = feedutil.to_utf8(enclosure['type'])
        except KeyError, e:
            raise FeedparserEntryError("Missing required data: %s" %
                    e.args[0])
        try:
            rv.size = feedutil.to_utf8(enclosure['length'])
        except KeyError:
            rv.size = None
        try:
            rv.date = datetime(*entry['updated_parsed'][:6])
        except KeyError:
            rv.date = None
        rv.thumbnail_url = feedutil.get_thumbnail_url(entry)
        return rv

    def __str__(self):
        return self.name

class ChannelMapperExtension(MapperExtension):
    def before_delete(self, mapper, connection, instance):
        delete = t.channel_subscription.delete(
                t.channel_subscription.c.channel_id==instance.id)
        connection.execute(delete)
        instance._subscriptions = None

category_select = select([t.category,
    util.count_subquery('channel_count', t.category_map.join(t.channel),
        t.channel.c.state=='A')
    ])

mapper(Category, category_select.alias())

mapper(TagMap, t.tag_map, properties={
    'tag': relation(Tag),
    'user': relation(User, backref=backref('tags', private=True)),
    })

tag_select = select([t.tag,
    util.aggregate_subquery('user_count',
        util.count_distinct(t.tag_map.c.user_id), t.tag_map),
    util.aggregate_subquery('channel_count',
        util.count_distinct(t.tag_map.c.channel_id),
        t.tag_map.join(t.channel),
        t.channel.c.state == Channel.APPROVED),
    ])

mapper(Tag, tag_select.alias(), properties={
    'channels': relation(Channel, secondary=t.tag_map),
    })

mapper(Item, t.item)

channel_select = select([t.channel,
    util.count_subquery('item_count', t.item),
    util.count_subquery('subscription_count', t.channel_subscription),
    util.count_subquery('subscription_count_today', t.channel_subscription,
        'timestamp > DATE_SUB(NOW(), INTERVAL 1 DAY)'),
    util.count_subquery('subscription_count_month', t.channel_subscription,
        'timestamp > DATE_SUB(NOW(), INTERVAL 1 MONTH)'),
    ])

channel_mapper = mapper(Channel, channel_select.alias(),
        extension=ChannelMapperExtension(), properties={
        'categories': relation(Category, secondary=t.category_map,
            backref='channels'),
        'items': relation(Item, private=True, backref='channel'),
        'tag_maps': relation(TagMap, private=True),
        'tags': relation(Tag, secondary=t.tag_map, viewonly=True),
        'owner': relation(User, backref=backref('channels', private=True)),
        'language': relation(Language),
        'secondary_languages': relation(Language,
            secondary=t.secondary_language_map),
    })
