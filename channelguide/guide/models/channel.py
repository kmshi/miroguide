# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from datetime import datetime, timedelta
from glob import glob
import cgi
import feedparser
import logging
import traceback
import time

from django.utils.translation import ngettext

from channelguide import util
from channelguide.guide import feedutil, tables, exceptions, emailmessages
from channelguide.guide.thumbnail import Thumbnailable
from channelguide.cache import client
from sqlhelper.orm import Record
from sqlhelper.sql import expression

from user import ModeratorAction, User
from item import Item
from label import Tag, TagMap
from rating import Rating, GeneratedRatings
import search

class Channel(Record, Thumbnailable):
    """An RSS feed containing videos for use in Miro."""
    table = tables.channel

    NEW = 'N'
    DONT_KNOW = 'D'
    REJECTED = 'R'
    APPROVED = 'A'
    AUDIO = 'U'
    BROKEN = 'B'
    SUSPENDED ='S'

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
        (85, 57), # recommended
        (98, 66), # new on front page
        (109, 73), # small on search page
        (132, 88), # search page
        (142, 96), # featured on front page
        (222, 146), # large image on details page
    ]

    def __str__(self):
        return "%s (%s)" % (self.name, self.url)

    def __repr__(self):
        return "Channel(%r, %r)" % (self.name, self.url)

    def get_state_name(self):
        return tables.name_for_state_code(self.state)
    state_name = property(get_state_name)

    @classmethod
    def query(cls, *args, **kwargs):
        if 'user' in kwargs:
            user = kwargs.pop('user')
        return super(Channel, cls).query(*args, **kwargs)

    @classmethod
    def query_approved(cls, *args, **kwargs):
        kwargs['state'] = cls.APPROVED
        return cls.query(*args, **kwargs)

    @classmethod
    def query_new(cls, *args, **kwargs):
        query = cls.query_approved(*args, **kwargs)
        query.where(cls.c.approved_at<=expression.Expression("SELECT timestamp FROM cg_channel_last_approved"))
        query.order_by(cls.c.approved_at, desc=True)
        return query

    @classmethod
    def query_with_items(cls, *args, **kwargs):
        query = Channel.query(*args, **kwargs).join('items')
        query.order_by(query.joins['items'].c.date, desc=True)
        return query

    @classmethod
    def get_channels(cls, connection, user, sort="name", filter=None,
            filter_value=None, limit=None, state='A', joins=None):
        select = cls.table.select()
        select.columns.append(cls.table.c.id)
        id_column = cls.table.c.id
        if state is not None:
            select.wheres.append(cls.table.c.state==state)
        if user is not None and user.adult_ok != True: # filter adult channels
            select.wheres.append(cls.c.adult==False)
        if sort == 'name':
            select.order_by.append('name')
        elif sort == 'rating':
            table = tables.generated_ratings
            join = cls.table.join(table, table.c.channel_id==id_column,
                    'LEFT')
            select.froms[0] = join
            select.wheres.append(table.c.count > 3)
            select.order_by.append('%s DESC' %
                    table.c.average.fullname())
            select.order_by.append('%s DESC' %
                    table.c.count.fullname())
        elif sort == 'new':
            select.order_by.append('approved_at DESC')
        elif sort.startswith('subscription_count'):
            table = tables.generated_stats
            join = cls.table.join(table, table.c.channel_id==id_column,
                    'LEFT')
            select.froms[0] = join
            if sort.endswith('today'):
                select.order_by.append('%s DESC' %
                        table.c.subscription_count_today.fullname())
            if not sort.endswith('count'):
                select.order_by.append('%s DESC' %
                        table.c.subscription_count_month.fullname())
            select.order_by.append('%s DESC' %
                    table.c.subscription_count_total.fullname())
        elif sort == 'count':
            wheres = select.wheres
            select = cls.table.select_count()
            select.wheres = wheres
            if joins and 'rating' in joins:
                # add a filter to remove channels that don't have enough ratings
                join = select.froms[0].join(tables.generated_ratings,
                        tables.generated_ratings.c.channel_id==id_column,
                        'LEFT')
                select.froms[0] = join
                select.wheres.append(tables.generated_ratings.c.count > 3)
        elif sort == 'random':
            select.order_by.append('RAND()')
        else:
            raise ValueError, 'unknown sort: %s' % sort
        if joins and sort != 'count':
            if 'subscriptions' in joins:
                table = tables.generated_stats
                if not sort.startswith('subscription_count'):
                    join = select.froms[0].join(table,
                            table.c.channel_id==id_column, 'LEFT')
                    select.froms[0] = join
                select.columns.append(table.c.subscription_count_total)
                select.columns.append(table.c.subscription_count_month)
                select.columns.append(table.c.subscription_count_today)
            if 'rating' in joins:
                table = tables.generated_ratings
                if sort != "rating":
                    join = select.froms[0].join(table,
                            table.c.channel_id==id_column, 'LEFT')
                    select.froms[0] = join
                select.columns.append(table.c.average)
                select.columns.append(table.c.count)
                select.columns.append(table.c.total)
        if filter is not None:
            if filter == 'category':
                join = select.froms[0].join(tables.category_map,
                    tables.category_map.c.channel_id==id_column, 'LEFT')
                select.froms[0] = join
                select.wheres.append(
                        tables.category_map.c.category_id==filter_value)
            elif filter == 'tag':
                join = select.froms[0].join(tables.tag_map,
                        tables.tag_map.c.channel_id==id_column, 'LEFT')
                select.froms[0] = join
                select.wheres.append(
                        tables.tag_map.c.tag_id==filter_value)
            elif filter == 'owner':
                select.wheres.append(
                    cls.table.c.owner_id==filter_value)
            elif filter == 'language':
                where1 = cls.table.c.primary_language_id==filter_value
                join = select.froms[0].join(tables.secondary_language_map,
                        tables.secondary_language_map.c.channel_id == id_column,
                        'LEFT')
                select.froms[0] = join
                where2 = \
                        tables.secondary_language_map.c.language_id==filter_value
                select.wheres.append(where1 | where2)
                s, a = select.compile()
            elif filter == 'featured':
                select.wheres.append(cls.table.c.featured==filter_value)
            else:
                raise ValueError, 'unknown filter: %s' % filter
        if limit:
            if isinstance(limit, int):
                select.limit = limit
            else:
                select.offset, select.limit = limit
        rows = select.execute(connection)
        if sort == 'count':
            return rows[0][0]
        ids = [row[0] for row in rows]
        channels = cls._get_records_from_cache(ids)
        _cache_key = cls._cache_key # put it in the local namespace
        missing = [id for id in ids if _cache_key(id) not in channels]
        if missing:
            rest = cls._get_records_from_db(connection, missing)
            channels.update(dict([(_cache_key(c.id), c) for c in rest]))
        list_of_channels = [channels[_cache_key(id)] for id in ids]
        if joins:
            iterator = iter(list_of_channels)
            for row in rows:
                channel = iterator.next()
                if 'subscriptions' in joins:
                    total, month, today = row[1:4]
                    channel.subscription_count_total = total
                    channel.subscription_count_month = month
                    channel.subscription_count_today = today
                if 'rating' in joins:
                    average, count, total = row[-3:]
                    channel.rating = GeneratedRatings()
                    channel.rating.channel_id = channel.id
                    channel.rating.average = average
                    channel.rating.count = count
                    channel.rating.total = total
        return list_of_channels

    def get_url(self):
        return util.make_url('channels/%d' % self.id)

    def get_absolute_url(self):
        return util.make_absolute_url('channels/%d' % self.id)

    def get_edit_url(self):
        return util.make_url('channels/edit/%d' % self.id)

    def subscription_link(self):
        cg_link = self.get_subscribe_hit_url()
        subscribe_link = self.get_subscription_url()
        return util.make_link_attributes(subscribe_link, "add",
                onclick="return handleSubscriptionLink('%s', '%s');" %
                (cg_link, subscribe_link))

    def get_subscribe_hit_url(self):
        return util.make_absolute_url('channels/subscribe-hit/%d' % self.id)
    
    def get_subscription_url(self):
        return util.get_subscription_url(self.url,
                                         trackback=self.get_subscribe_hit_url())

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

        subscription_table = tables.channel_subscription_holding
        select = subscription_table.select_count()
        select.wheres.append(subscription_table.c.ip_address==ip_address)
        second_ago = timestamp - timedelta(seconds=1)
        select.wheres.append(subscription_table.c.timestamp > second_ago)
        return select.execute_scalar(connection) > 0

    def add_subscription(self, connection, ip_address, timestamp=None, ignore_for_recommendations=False):
        if self.id is None:
            msg = "Channel must be saved before add_subscription() is called"
            raise ValueError(msg)
        if timestamp is None:
            timestamp = datetime.now()
        if self._should_throttle_ip_address(connection, ip_address, timestamp):
            return
        insert = tables.channel_subscription_holding.insert()
        insert.add_values(channel_id=self.id, ip_address=ip_address,
                timestamp=timestamp,
                ignore_for_recommendations=ignore_for_recommendations)
        insert.execute(connection)

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
        for item in self.items[::-1]:
            try:
                item.refresh_thumbnails(overwrite, sizes)
            except: pass

    def download_item_thumbnails(self, connection, redownload=False):
        """Download item thumbnails."""

        for item in self.items:
            try:
                item.download_thumbnail(connection, redownload)
            except:
                pass

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
        client.set('search', time.time()) # reset search cache

    def get_search_data(self):
        simple_attrs = ('description', 'url',
                'website_url', 'publisher')
        values = [getattr(self, attr) for attr in simple_attrs]
        values.append(self.language.name)
        for attr in ('tags', 'categories', 'secondary_languages'):
            for obj in getattr(self, attr):
                values.append(obj.name)
        values = [util.unicodify(v) for v in values]
        return u' '.join(values)

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
                    self._check_archived(connection)
                    return
            else:
                parsed = feedparser.parse(feedparser_input)
        except:
            print "WARNING: ERROR parsing %s" % self.url
            traceback.print_exc()
        else:
            items = []
            for entry in parsed.entries:
                try:
                    items.append(Item.from_feedparser_entry(entry))
                except exceptions.EntryMissingDataError:
                    pass
                except exceptions.FeedparserEntryError, e:
                    logging.warn("Error converting feedparser entry: %s (%s)" 
                            % (e, self))
            self._replace_items(connection, items)
        if self.items:
            self._check_archived(connection)

    def _check_archived(self, connection):
        latest = None
        items = [item for item in self.items if item.date is not None]
        if not items:
            return
        items.sort(key=lambda x: x.date)
        latest = items[-1].date
        if (datetime.now() - latest).days > 90:
            self.archived = True
        else:
            self.archived = False
        self.save(connection)

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
        return util.mark_safe('<img src="%s" alt="%s">' % (thumb_url, cgi.escape(self.name)))
        
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
            self.join('items').execute(connection)
            self.update_items(connection)
        else:
            self.approved_at = None
        self.last_moderated_by_id = user.id
        self.save(connection)
        ModeratorAction(user, self, newstate).save(connection)

    def change_featured(self, user, connection):
        if user is not None:
            self.featured = True
            self.featured_at = datetime.now()
            self.featured_by_id = user.id
        else:
            self.featured = False
            self.featured_at = None
            self.featured_by_id = None
        self.save(connection)

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

    def rate(self, connection, user, score):
        self.join('rating').execute(connection)
        query = Rating.query(channel_id=self.id, user_id=user.id)
        try:
            rating = query.get(connection)
        except:
            rating = Rating()
            rating.channel_id = self.id
            rating.user_id = user.id
            rating.rating = None
        if rating.rating:
            self.rating.count -= 1
            self.rating.total -= rating.rating
        rating.rating = int(score)
        rating.timestamp = datetime.now()
        if rating.rating == 0:
            rating.rating = None
        elif user.approved:
            if self.rating:
                self.rating.count += 1
                self.rating.total += rating.rating
                self.rating.average = float(self.rating.total) / self.rating.count
                self.rating.save(connection)
            else:
                self.rating = ge = GeneratedRatings()
                ge.channel_id = self.id
                ge.average = ge.total = rating.rating
                ge.count = 1
                ge.save(connection)
        rating.save(connection)
        return rating

for width, height in Channel.THUMBNAIL_SIZES:
    def thumb(self, width=width, height=height):
        return self._thumb_html(width, height)
    setattr(Channel, 'thumb_%i_%i' % (width, height), thumb)
    del thumb
