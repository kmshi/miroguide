from datetime import datetime, timedelta
from glob import glob
from urllib import quote
import cgi
import feedparser
import logging
import traceback
import math

from django.conf import settings
from django.utils.translation import ngettext

from channelguide import util
from channelguide.guide import feedutil, tables, exceptions, emailmessages
from channelguide.guide.thumbnail import Thumbnailable
from sqlhelper.orm import Record
from sqlhelper.sql import expression

from user import ModeratorAction, User
from item import Item
from label import Tag, TagMap
import search

class Channel(Record, Thumbnailable):
    """An RSS feed containing videos for use in Miro."""
    table = tables.channel

    NEW = 'N'
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

    def __repr__(self):
        return "Channel(%r, %r)" % (self.name, self.url)

    def get_state_name(self):
        return tables.name_for_state_code(self.state)
    state_name = property(get_state_name)

    @classmethod
    def query_approved(cls, *args, **kwargs):
        kwargs['state'] = cls.APPROVED
        return cls.query(*args, **kwargs)

    @classmethod
    def query_with_items(cls, *args, **kwargs):
        query = Channel.query(*args, **kwargs).join('items')
        query.order_by(query.joins['items'].c.date, desc=True)
        return query

    def get_url(self):
        return util.make_url('channels/%d' % self.id)

    def get_absolute_url(self):
        return util.make_absolute_url('channels/%d' % self.id)

    def get_edit_url(self):
        return util.make_url('channels/edit/%d' % self.id)

    def subscription_link(self):
        cg_link = util.make_url('channels/subscribe-hit/%d' %
                self.id)
        subscribe_link = settings.SUBSCRIBE_URL % { 'url': quote(self.url) }
        return util.make_link_attributes(subscribe_link, "add",
                onclick="return handleSubscriptionLink('%s', '%s');" %
                (cg_link, subscribe_link))

    def get_subscription_url(self):
        return util.make_url('channels/subscribe/%d' % self.id)

    def is_approved(self):
        return self.state == self.APPROVED

    def add_note(self, connection, note):
        self.join('notes').execute(connection)
        self.notes.add_record(connection, note)
        if note.user_id == self.owner_id:
            self.waiting_for_reply_date = datetime.now()
            self.save(connection)
        elif self.waiting_for_reply_date is not None:
            self.waiting_for_reply_date = None
            self.save(connection)

    def add_tag(self, connection, user, tag_name):
        """Add a tag to this channel."""
        try:
            tag = Tag.query(name=tag_name).get(connection)
        except LookupError:
            tag = Tag(tag_name)
            tag.save(connection)
        query = TagMap.query()
        query.where(channel_id=self.id, user_id=user.id, tag_id=tag.id)
        if query.count(connection) == 0:
            tm = TagMap(self, user, tag)
            tm.save(connection)

    def delete_tag(self, connection, user, tag_name):
        try:
            tag = Tag.query(name=tag_name).get(connection)
        except LookupError:
            return
        try:
            tag_map = TagMap.get(connection, (self.id, user.id, tag.id))
        except LookupError:
            return
        tag_map.delete(connection)

    def add_tags(self, connection, user, tags):
        """Tag this channel with a list of tags."""
        for tag in tags:
            self.add_tag(connection, user, tag)

    def get_tags_for_user(self, connection, user):
        query = TagMap.query().join('tag')
        query.where(user_id=user.id, channel_id=self.id)
        return [map.tag for map in query.execute(connection)]

    def get_tags_for_owner(self, connection):
        self.join('owner').execute(connection)
        return self.get_tags_for_user(connection, self.owner)

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

    def _should_throttle_ip_address(self, connection, ip_address, timestamp):
        """Check to see if we got a subscription from the same ip address too
        recently.
        """

        subscription_table = tables.channel_subscription
        select = subscription_table.select_count()
        select.wheres.append(subscription_table.c.ip_address==ip_address)
        week_ago = timestamp - timedelta(weeks=1)
        select.wheres.append(subscription_table.c.timestamp > week_ago)
        return select.execute_scalar(connection) > 0

    def add_subscription(self, connection, ip_address, timestamp=None):
        if self.id is None:
            msg = "Channel must be saved before add_subscription() is called"
            raise ValueError(msg)
        if timestamp is None:
            timestamp = datetime.now()
#        if self._should_throttle_ip_address(connection, ip_address, timestamp):
#            return
        insert = tables.channel_subscription.insert()
        insert.add_values(channel_id=self.id, ip_address=ip_address,
                timestamp=timestamp)
        insert.execute(connection)
        self.recalculate_recommendations(connection, ip_address)

    def recalculate_recommendations(self, connection, ip_address):
        if ip_address == '0.0.0.0':
            return # don't bother with no IP
        updates = self.find_relevant_similar(connection, ip_address)
        self.delete_old_recommendations(connection, updates)
        for channel in updates:
            self.insert_recommendation(connection, channel)

    def insert_recommendation(self, connection, other):
        recommendation = self.get_similarity(connection, other)
        if recommendation == 0:
            return
        c1, c2 = self.id, other
        if c1 > c2:
            c1, c2 = c2, c1
        insert = tables.channel_recommendations.insert()
        insert.add_values(channel1_id=c1, channel2_id=c2,
                cosine=recommendation)
        insert.execute(connection)

    def delete_old_recommendations(self, connection, channels):
        for c in channels:
            c1 = self.id
            c2 = c
            if c1 > c2:
                c1, c2 = c2, c1
            delete = tables.channel_recommendations.delete()
            delete.wheres.append(
                    tables.channel_recommendations.c.channel1_id==c1)
            delete.wheres.append(
                tables.channel_recommendations.c.channel2_id==c2)
            delete.execute(connection)

    def find_relevant_similar(self, connection, ip_address):
        sql = """SELECT DISTINCT channel_id FROM cg_channel_subscription WHERE
    (channel_id<>%s AND ip_address=%s)"""
        results = connection.execute(sql, (self.id, ip_address))
        return [e[0] for e in results]

    def get_similarity(self, connection, other):
        sql = 'SELECT channel_id, ip_address from cg_channel_subscription WHERE channel_id=%s OR channel_id=%s ORDER BY ip_address'
        entries = connection.execute(sql, (self.id, other))
        if not entries:
            return 0.0
        vectors = {}
        for (channel, ip) in entries:
            vectors.setdefault(ip, [False, False])
            i = int(channel)
            if i == self.id:
                vectors[ip][0] = True
            elif i == other:
                vectors[ip][1] = True
            else:
                raise RuntimeError("%r != to %r or %r" % (i, self.id, other))
        keys = vectors.keys()
        keys.sort()
        v1 = [vectors[k][0] for k in keys]
        v2 = [vectors[k][1] for k in keys]
        return cosine(v1, v2)

    def update_thumbnails(self, connection, overwrite=False, sizes=None):
        """Recreate the thumbnails using the original data."""

        if self.thumbnail_extension is None:
            pattern = self.thumb_path('original')
            pattern = pattern.replace("missing.png", "%d.*" % self.id)
            matches = glob(pattern)
            if matches:
                data = util.read_file(matches[0])
                self.thumbnail_extension = util.get_image_extension(data)
                self.save(connection)

        Thumbnailable.refresh_thumbnails(self, overwrite, sizes)
        for item in self.items:
            item.refresh_thumbnails(overwrite, sizes)

    def download_item_thumbnails(self, connection, redownload=False):
        """Download item thumbnails."""

        for item in self.items:
            item.download_thumbnail(connection, redownload)

    def update_search_data(self, connection):
        self.join("search_data", "items", 'tags', 'categories',
                'secondary_languages', 'language').execute(connection)
        if self.search_data is None:
            self.search_data = search.ChannelSearchData()
            self.search_data.channel_id = self.id
        self.search_data.text = self.get_search_data()
        self.search_data.important_text = self.name
        self.search_data.save(connection)
        for item in self.items:
            item.update_search_data(connection)

    def get_search_data(self):
        simple_attrs = ('short_description', 'description', 'url',
                'website_url', 'publisher')
        values = [getattr(self, attr) for attr in simple_attrs]
        values.append(self.language.name)
        for attr in ('tags', 'categories', 'secondary_languages'):
            for obj in getattr(self, attr):
                values.append(obj.name)
        values = [v.decode('utf-8') for v in values]
        return u' '.join(values).encode('utf-8')

    def get_missing_image_url(self, width, height):
        return ''

    def fix_utf8_strings(self, connection):
        if feedutil.fix_utf8_strings(self):
            self.save(connection)
        for item in self.items:
            if feedutil.fix_utf8_strings(item):
                item.save(connection)

    def download_feed(self):
        if self.feed_modified:
            modified = self.feed_modified.timetuple()
        else:
            modified = None
        parsed = feedparser.parse(self.url, modified=modified,
                etag=self.feed_etag)
        if hasattr(parsed, 'status') and parsed.status == 304:
            return None
        if hasattr(parsed, 'modified'):
            new_modified = feedutil.struct_time_to_datetime(parsed.modified)
            if (self.feed_modified is not None and 
                    new_modified <= self.feed_modified):
                return None
            self.feed_modified = new_modified
        if hasattr(parsed, 'etag'):
            self.feed_etag = parsed.etag
        return parsed

    def update_items(self, connection, feedparser_input=None):
        try:
            if feedparser_input is None:
                parsed = self.download_feed()
                if parsed is None:
                    return
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
            self._replace_items(connection, items)

    def _replace_items(self, connection, new_items):
        """Replace the items currently in the channel with a new list of
        items."""

        to_delete = set(self.items)
        to_add = set(new_items)

        items_by_url = {}
        items_by_guid = {}
        for i in self.items:
            if i.url is not None:
                items_by_url[i.url] = i
            if i.get_guid() is not None:
                items_by_guid[i.get_guid()] = i
        for i in new_items:
            if i.get_guid() in items_by_guid:
                to_delete.discard(items_by_guid[i.get_guid()])
                to_add.discard(i)
            elif i.url in items_by_url:
                to_delete.discard(items_by_url[i.url])
                to_add.discard(i)
        for i in to_delete:
            self.items.remove_record(connection, i)
        for i in new_items:
            if i in to_add:
                self.items.add_record(connection, i)

    def _thumb_html(self, width, height):
        thumb_url = self.thumb_url(width, height)
        return '<img src="%s" alt="%s">' % (thumb_url, cgi.escape(self.name))

    def thumb_60_40(self): return self._thumb_html(60, 40)
    def thumb_120_80(self): return self._thumb_html(120, 80)
    def thumb_165_110(self): return self._thumb_html(165, 110)
    def thumb_252_169(self): return self._thumb_html(252, 169)
    def thumb_370_247(self): return self._thumb_html(370, 247)

    def fake_feature_thumb(self): 
        thumb_url = self.thumb_url(252, 169)
        return 'src: "%s" alt:"%s"' % (thumb_url, cgi.escape(self.name))

    def name_as_link(self):
        return util.make_link(self.get_absolute_url(), self.name)

    def website_link(self):
        url_label = self.website_url
        url_label = util.chop_prefix(url_label, 'http://')
        url_label = util.chop_prefix(url_label, 'https://')
        url_label = util.chop_prefix(url_label, 'www.')
        return util.make_link(self.website_url, url_label)

    def change_state(self, user, newstate, connection):
        self.state = newstate
        if newstate == self.APPROVED:
            self.approved_at = datetime.now()
            self.join('owner').execute(connection)
            if self.owner.email is not None:
                emailmessages.ApprovalEmail(self, self.owner).send_email()
            else:
                logging.warn('not sending approval message for channel %d '
                        '(%s) because the owner email is not set', self.id,
                        self.name)

        else:
            self.approved_at = None
        self.last_moderated_by_id = user.id
        self.save(connection)
        ModeratorAction(user, self, newstate).save(connection)

    def feature(self, connection):
        self.featured = True
        self.featured_at = datetime.now()

    def toggle_moderator_share(self, user):
        if self.moderator_shared_at is None:
            self.moderator_shared_at = datetime.now()
            self.moderator_shared_by_id = user.id
        else:
            self.moderator_shared_at = None
            self.moderator_shared_by_id = 0

    def update_moderator_shared_by(self, connection):
        if self.moderator_shared_at is not None:
            if self.moderator_shared_by_id != 0:
                user = User.query(id=self.moderator_shared_by_id).get(connection)
                self.moderator_shared_by = user

    def get_moderator_shared_by(self):
        if self.moderator_shared_at is None:
            return None
        if self.moderator_shared_by_id == 0:
            return None
        return self.moderator_shared_by

def dotProduct(vector1, vector2):
    return sum([v1*v2 for v1, v2 in zip(vector1, vector2)])

def length(vector):
    return math.sqrt(sum([v**2 for v in vector]))

def cosine(v1, v2):
    l1 = length(v1)
    l2 = length(v2)
    if l1 == 0 or l2 == 0:
        return 0.0
    return dotProduct(v1, v2)/(l1 * l2)


