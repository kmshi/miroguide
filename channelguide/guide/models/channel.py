from datetime import datetime
from glob import glob
import logging
import traceback

from django.utils.translation import ngettext
from sqlalchemy import select

from channelguide.db import DBObject
from channelguide import util
from channelguide.guide import feedutil, tables, exceptions
from channelguide.guide.thumbnail import Thumbnailable
from channelguide.lib import feedparser

from search import FullTextSearchable, ChannelSearchData
from item import Item
from label import Tag, TagMap

class Channel(DBObject, Thumbnailable, FullTextSearchable):
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
        db_session = self.session()
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

    def refresh_search_data(self):
        FullTextSearchable.refresh_search_data(self)
        for item in self.items:
            item.refresh_search_data()

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

    def _replace_items(self, items):
        """Replace the items currently in the channel with a new list of
        items."""

        db_session = self.session()
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

    @classmethod
    def search_items(cls, db_session, query, limit=None):
        connection = db_session.connection(cls.mapper())
        item_ids = Item.id_search(connection, query)
        q = db_session.query(Channel)
        select = q.select(q.join_to('items') & Item.c.id.in_(*item_ids))
        if limit is not None:
            select.limit(limit)
        return select.list()
