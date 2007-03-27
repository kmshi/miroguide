from datetime import datetime
from glob import glob
from urllib import quote
import feedparser
import logging
import traceback

from django.conf import settings
from django.utils.translation import ngettext
from sqlalchemy import select, desc, func, eagerload

from channelguide.db import DBObject, dbutil
from channelguide import util
from channelguide.guide import feedutil, tables, exceptions
from channelguide.guide.thumbnail import Thumbnailable

from item import Item
from label import Tag, TagMap
import search

class Channel(DBObject, Thumbnailable):
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

    def __str__(self):
        return "%s (%s)" % (self.name, self.url)

    def get_absolute_url(self):
        return util.make_absolute_url('channels/%d' % self.id)

    def get_edit_url(self):
        return util.make_absolute_url('channels/edit/%d' % self.id)

    def subscription_link(self):
        cg_link = util.make_absolute_url('channels/subscribe-hit/%d' %
                self.id)
        subscribe_link = settings.SUBSCRIBE_URL % { 'url': quote(self.url) }
        return util.make_link_attributes('#', "add",
                onclick="return handleSubscriptionLink('%s', '%s');" %
                (cg_link, subscribe_link))

    def get_subscription_url(self):
        return util.make_absolute_url('channels/subscribe/%d' % self.id)

    def is_approved(self):
        return self.state == self.APPROVED

    def add_tag(self, user, tag_name):
        """Add a tag to this channel."""
        db_session = self.session()
        tag = db_session.query(Tag).get_by(name=tag_name)
        if tag is None:
            tag = Tag(tag_name)
            db_session.save(tag)
            db_session.flush([tag])
        if not db_session.get(TagMap, (self.id, user.id, tag.id)):
            self.tag_maps.append(TagMap(self, user, tag))

    def delete_tag(self, user, tag_name):
        db_session = self.session()
        tag = db_session.query(Tag).get_by(name=tag_name)
        if tag is not None:
            tag_map = db_session.get(TagMap, (self.id, user.id, tag.id))
            if tag_map is not None:
                db_session.delete(tag_map)

    def get_tags_for_user(self, user):
        db_session = self.session()
        q = db_session.query(TagMap).options(eagerload('tag'))
        return [m.tag for m in q.select_by(user=user, channel=self)]

    def get_tags_for_owner(self):
        return self.get_tags_for_user(self.owner)

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
        connection.execute(tables.channel_subscription.insert(), values)

    def update_thumbnails(self, overwrite=False, redownload=False, sizes=None):
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
            item.download_thumbnail(redownload)
            item.refresh_thumbnails(overwrite, sizes)

    def update_search_data(self):
        if self.search_data is None:
            self.search_data = search.ChannelSearchData()
            self.session().save(self.search_data)
        self.search_data.text = self.get_search_data()
        self.search_data.important_text = self.name
        for item in self.items:
            item.update_search_data()

    def get_search_data(self):
        simple_attrs = ('short_description', 'description', 'url',
                'website_url', 'publisher')
        values = [getattr(self, attr) for attr in simple_attrs]
        values.append(self.language.name)
        for attr in ('tags', 'categories', 'secondary_languages'):
            for obj in getattr(self, attr):
                values.append(obj.name)
        return ' '.join(values)

    def get_missing_image_url(self, width, height):
        return ''

    @staticmethod
    def do_search(db_session, terms, offset, limit, where):
        query = db_session.query(Channel)
        where &= query.join_to('search_data')
        score = search.score_column(search.ChannelSearchData, terms)
        sql_query = select(list(Channel.c) + [score.label('score')], where)
        sql_query.order_by(desc('score'))
        sql_query.offset = offset
        sql_query.limit = limit
        results = db_session.connection(Channel.mapper()).execute(sql_query)
        return query.instances(results)

    @staticmethod
    def search(db_session, terms, offset=0, limit=None):
        if not isinstance(terms, list):
            terms = [terms]
        where = search.where_clause(search.ChannelSearchData, terms)
        return Channel.do_search(db_session, terms, offset, limit, where)

    @staticmethod
    def search_count(connection, terms):
        if not isinstance(terms, list):
            terms = [terms]
        where = search.where_clause(search.ChannelSearchData, terms)
        sql_query = tables.channel.join(tables.channel_search_data).count(where)
        return connection.execute(sql_query).scalar()

    @staticmethod
    def search_items(db_session, terms, offset=0, limit=None):
        if not isinstance(terms, list):
            terms = [terms]
        channel_ids = Item.search_for_channel_ids(db_session, terms)
        where = Channel.c.id.in_(*channel_ids)
        return Channel.do_search(db_session, terms, offset, limit, where)

    @staticmethod
    def search_items_count(connection, terms):
        if not isinstance(terms, list):
            terms = [terms]
        where = search.where_clause(search.ItemSearchData, terms)
        sql_query = select([dbutil.count_distinct(tables.item.c.channel_id)],
                where, from_obj=[tables.item.join(tables.item_search_data)])
        return connection.execute(sql_query).scalar()

    def fix_utf8_strings(self):
        feedutil.fix_utf8_strings(self)
        for item in self.items:
            feedutil.fix_utf8_strings(item)

    def update_items(self, feedparser_input=None):
        try:
            if feedparser_input is None:
                parsed = feedparser.parse(self.url,
                        modified=self.feed_modified,
                        etag=self.feed_etag)
                if hasattr(parsed, 'status') and parsed.status == 304:
                    return
                if hasattr(parsed, 'modified'):
                    if (self.feed_modified is not None and 
                            parsed.modified <= self.feed_modified):
                        return
                    self.feed_modified = parsed.modified
                if hasattr(parsed, 'etag'):
                    self.feed_etag = parsed.etag
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
                except exceptions.EntryMissingDataError:
                    pass
                except exceptions.FeedparserEntryError, e:
                    logging.warn("Error converting feedparser entry: %s (%s)" 
                            % (e, self))
            self._replace_items(items)

    def _replace_items(self, new_items):
        """Replace the items currently in the channel with a new list of
        items."""

        to_delete = set(self.items)
        to_add = set(new_items)

        items_by_url = {}
        items_by_guid = {}
        for i in self.items:
            if i.url is not None:
                items_by_url[i.url] = i
            if i.id is not None:
                items_by_guid[i.id] = i
        for i in new_items:
            if i.id in items_by_guid:
                to_delete.discard(items_by_guid[i.id])
                to_add.discard(i)
            elif i.url in items_by_url:
                to_delete.discard(items_by_url[i.url])
                to_add.discard(i)
        db_session = self.session()
        for i in to_delete:
            db_session.delete(i)
        for i in new_items:
            if i in to_add:
                self.items.append(i)
                db_session.save(i)

    def _thumb_html(self, width, height):
        thumb_url = self.thumb_url(width, height)
        return '<img src="%s" alt="%s">' % (thumb_url, self.name)

    def thumb_60_40(self): return self._thumb_html(60, 40)
    def thumb_120_80(self): return self._thumb_html(120, 80)
    def thumb_165_110(self): return self._thumb_html(165, 110)
    def thumb_252_169(self): return self._thumb_html(252, 169)
    def thumb_370_247(self): return self._thumb_html(370, 247)

    def name_as_link(self):
        return util.make_link(self.get_absolute_url(), self.name)

    def website_link(self):
        url_label = self.website_url
        url_label = util.chop_prefix(url_label, 'http://')
        url_label = util.chop_prefix(url_label, 'https://')
        url_label = util.chop_prefix(url_label, 'www.')
        return util.make_link(self.website_url, url_label)

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
