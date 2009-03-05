# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from datetime import datetime, timedelta
import os
import time
from urllib2 import URLError

from django.conf import settings
from django.template import loader

from channelguide import util, manage, cache
from channelguide.guide.models import (Channel, Category, Tag, Item, User,
        Language, TagMap, AddedChannel, ModeratorAction)
from channelguide.testframework import TestCase

def test_data_path(filename):
    return os.path.join(os.path.dirname(__file__), 'data', filename)

def test_data_url(filename):
    return 'file://' + os.path.abspath(test_data_path(filename))

class ChannelTestBase(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.ralph = self.make_user('ralph')
        Channel.table.record_class = Channel
        self.channel = self.make_channel()
        join = self.channel.join('items', 'tags', 'categories', 'owner',
                'last_moderated_by', 'featured_by')
        join.execute(self.connection)

    def make_channel(self, **kwargs):
        return TestCase.make_channel(self, self.ralph, **kwargs)

class ChannelTagTest(ChannelTestBase):
    """Test adding/removing/querying tags from channels."""

    def setUp(self):
        ChannelTestBase.setUp(self)
        self.ben = self.make_user('ben')
        self.nick = self.make_user('nick')

    def check_tags(self, *correct_tags):
        channel = Channel.get(self.connection, self.channel.id)
        channel.join('tags').execute(self.connection)
        current_tags = [tag.name for tag in channel.tags]
        self.assertSameSet(current_tags, correct_tags)

    def test_tags(self):
        self.channel.add_tag(self.connection, self.ben, 'funny')
        self.check_tags('funny')
        self.channel.add_tag(self.connection, self.ben, 'cool')
        self.check_tags('funny', 'cool')
        self.channel.add_tags(self.connection, self.nick, ['sexy', 'cool'])
        self.check_tags('funny', 'cool', 'sexy')
        self.channel.add_tag(self.connection, self.nick, 'cool')
        self.check_tags('funny', 'cool', 'sexy')

    def test_duplicate_tags(self):
        self.channel.add_tag(self.connection, self.ben, 'funny')
        self.channel.add_tag(self.connection, self.nick, 'funny')
        count = Tag.query(name='funny').count(self.connection)
        self.assertEquals(count, 1)

    def check_tag_counts(self, name, user_count, channel_count):
        query = Tag.query(name=name).load('user_count', 'channel_count')
        tag = query.get(self.connection)
        self.assertEquals(tag.user_count, user_count)
        self.assertEquals(tag.channel_count, channel_count)

    def test_info(self):
        self.channel.state = Channel.APPROVED
        self.channel.add_tag(self.connection, self.ben, 'funny')
        self.channel.add_tag(self.connection, self.nick, 'funny')
        self.channel.save(self.connection)
        self.check_tag_counts('funny', 2, 1)
        channel2 = self.make_channel(state=Channel.APPROVED)
        channel2.add_tags(self.connection, self.ben, ['tech', 'funny'])
        self.channel.add_tag(self.connection, self.ben, 'tech')
        self.check_tag_counts('funny', 2, 2)
        self.check_tag_counts('tech', 1, 2)
        non_active = self.make_channel()
        non_active.add_tag(self.connection, self.nick, 'funny')
        non_active.add_tag(self.connection, self.ben, 'funny')
        self.check_tag_counts('funny', 2, 2)
        self.check_tag_counts('funny', 2, 2)

class ChannelModelTest(ChannelTestBase):
    """Test operations on the Channel class."""

    def get_thumb_path(self, subdir):
        file = "%d.jpeg" % self.channel.id
        return os.path.join(settings.MEDIA_ROOT, Channel.THUMBNAIL_DIR,
                subdir, file)

    def check_thumb_exists(self, subdir):
        self.assert_(os.path.exists(self.get_thumb_path(subdir)))

    def test_thumbnail(self):
        image_data = util.read_file(test_data_path('thumbnail.jpg'))
        self.channel.save_thumbnail(self.connection, image_data)
        self.check_thumb_exists('original')
        for width, height in Channel.THUMBNAIL_SIZES:
            self.check_thumb_exists('%ix%i' % (width, height))
        self.assertEquals(image_data,
                util.read_file(self.get_thumb_path('original')))

    def test_approved_at(self):
        self.assertEquals(self.channel.approved_at, None)
        self.channel.change_state(self.ralph, Channel.APPROVED,
                self.connection)
        timediff = datetime.now() - self.channel.approved_at
        self.assert_(timediff < timedelta(seconds=1))
        self.assert_(timediff > timedelta(seconds=0))
        self.channel.change_state(self.ralph, Channel.NEW, self.connection)
        self.assertEquals(self.channel.approved_at, None)

    def test_approve_email(self):
        self.channel.change_state(self.ralph, Channel.APPROVED,
                self.connection)
        self.assertEquals(len(self.emails), 1)
        self.assertEquals(self.emails[0]['recipient_list'],
                [self.channel.owner.email])

    def test_approval_queue(self):
        self.assertEquals(len(self.channel.query_new().execute(
            self.connection)), 0)
        time.sleep(1)
        self.channel.change_state(self.ralph, Channel.APPROVED,
                self.connection)
        time.sleep(1) # make sure they have different timestamps
        c2 = self.make_channel()
        c2.change_state(self.ralph, Channel.APPROVED,
                self.connection)
        self.assertEquals(len(self.channel.query_new().execute(
            self.connection)), 0)
        manage.update_new_channel_queue()
        self.refresh_connection()
        new_channels = self.channel.query_new().execute(
                self.connection)
        self.assertEquals(len(new_channels), 1)
        self.assertEquals(new_channels[0].id, self.channel.id)
        manage.update_new_channel_queue()
        self.refresh_connection()
        new_channels = self.channel.query_new().execute(
                self.connection)
        self.assertEquals(len(new_channels), 2)
        self.assertEquals(new_channels[0].id, c2.id)

    def test_last_moderated_by(self):
        self.assertEquals(self.channel.last_moderated_by, None)
        self.channel.change_state(self.ralph, Channel.APPROVED,
                self.connection)
        channel2 = self.refresh_record(self.channel, 'last_moderated_by')
        self.assertEquals(channel2.last_moderated_by.id, self.ralph.id)

    def test_thumbnail_before_save(self):
        c = Channel()
        c.url = "http://myblog.com/videos/rss"
        c.website_url = "http://myblog.com/"
        c.publisher = "TestVision"
        c.description = "lots of stuff"
        self.assertRaises(ValueError, c.save_thumbnail,
                self.connection,
                util.read_file(test_data_path('thumbnail.jpg')))

    def check_subscription_counts(self, total, month, today):
        subscription_count_today = self.connection.execute('SELECT COUNT(*) FROM cg_channel_subscription_holding WHERE channel_id=%s and timestamp>DATE_SUB(NOW(), INTERVAL 1 DAY)', self.channel.id)[0][0]
        subscription_count_month = self.connection.execute('SELECT COUNT(*) FROM cg_channel_subscription_holding WHERE channel_id=%s and timestamp>DATE_SUB(NOW(), INTERVAL 1 MONTH)', self.channel.id)[0][0]
        subscription_count = self.connection.execute('SELECT COUNT(*) FROM cg_channel_subscription_holding WHERE channel_id=%s', self.channel.id)[0][0]
        self.assertEquals(subscription_count, total)
        self.assertEquals(subscription_count_month, month)
        self.assertEquals(subscription_count_today, today)

    def test_subscription_counts(self):
        now = datetime.now()
        week = timedelta(days=7)

        self.check_subscription_counts(0, 0, 0)
        self.channel.add_subscription(self.connection, '1.1.1.1', now)
        self.check_subscription_counts(1, 1, 1)
        self.channel.add_subscription(self.connection, '1.1.1.2', now-week*1)
        self.check_subscription_counts(2, 2, 1)
        self.channel.add_subscription(self.connection, '1.1.1.3', now-week*6)
        self.check_subscription_counts(3, 2, 1)

    def test_subscription_spam_prevention(self):
        now = datetime.now()
        next_week = now + timedelta(days=7)
        self.channel.add_subscription(self.connection, '1.1.1.1', now)
        self.check_subscription_counts(1, 1, 1)
        self.channel.add_subscription(self.connection, '1.1.1.1', now)
        self.check_subscription_counts(1, 1, 1)
        self.channel.add_subscription(self.connection, '1.1.1.1', next_week)
        self.check_subscription_counts(2, 2, 2)

    def test_stats_refresh(self):
        """
        Test that manage.refresh_stats_table() correctly updates the
        subscription table.
        """
        now = datetime.now()
        week = timedelta(days=7)
        self.channel.state = 'A'
        self.channel.save(self.connection)
        self.channel.add_subscription(self.connection, '1.1.1.1', now)
        self.channel.add_subscription(self.connection, '1.1.1.2', now-week*1)
        self.channel.add_subscription(self.connection, '1.1.1.3', now-week*6)
        self.refresh_connection()
        manage.refresh_stats_table()
        self.refresh_connection()
        q = self.channel.query()
        chan = q.join('stats').get(self.connection, self.channel.id)
        self.assertEquals(chan.stats.subscription_count_total, 3)
        self.assertEquals(chan.stats.subscription_count_month, 2)
        self.assertEquals(chan.stats.subscription_count_today, 1)

    def check_tag_map_count(self, correct_count):
        tag_count = TagMap.query().count(self.connection)
        self.assertEquals(tag_count, correct_count)

    def test_delete(self):
        ben = self.make_user('ben')
        self.channel.add_subscription(self.connection, '1.1.1.1')
        self.channel.add_tag(self.connection, ben, 'cool')
        self.check_tag_map_count(1)
        self.channel.delete(self.connection)
        self.check_tag_map_count(0)

    def test_delete_user_with_tags(self):
        ben = self.make_user('ben')
        self.channel.add_tag(self.connection, ben, 'cool')
        self.check_tag_map_count(1)
        ben.delete(self.connection)
        self.check_tag_map_count(0)

    def test_category_counts(self):
        def test(cat, test_count):
            query = Category.query(id=cat.id).load('channel_count')
            cat = query.get(self.connection)
            self.assertEquals(cat.channel_count, test_count)
        foo = Category(name='foo')
        bar = Category(name='bar')
        self.save_to_db(foo, bar)
        test(foo, 0)
        test(bar, 0)
        channel = self.make_channel(state=Channel.APPROVED)
        non_active = self.make_channel()
        channel.join('categories').execute(self.connection)
        non_active.join('categories').execute(self.connection)
        channel.categories.add_record(self.connection, foo)
        non_active.categories.add_record(self.connection, bar)
        test(foo, 1)
        test(bar, 0)

    def test_featured_by(self):
        self.assertEquals(self.channel.featured_by, None)
        self.channel.change_featured(self.ralph, self.connection)
        self.channel.save(self.connection)
        channel2 = self.refresh_record(self.channel, 'featured_by')
        self.assertEquals(channel2.featured_by.id, self.ralph.id)
        channel2.change_featured(None, self.connection)
        channel3 = self.refresh_record(self.channel, 'featured_by')
        self.assertEquals(self.channel.featured_by, None)


class ChannelItemTest(ChannelTestBase):
    def check_item_titles(self, *correct_titles):
        self.assertEquals(len(self.channel.items), len(correct_titles))
        for i in range(len(correct_titles)):
            self.assertEquals(self.channel.items[i].name, correct_titles[i])

    def update_channel(self):
        """
        Refresh the default channel and rejoin the items.  Useful for
        refreshing before update_items().
        """
        self.channel = self.refresh_record(self.channel)
        self.channel.join('items').execute(self.connection)

    def test_parse(self):
        self.channel.update_items(self.connection,
                feedparser_input=open(test_data_path('feed.xml')))
        self.check_item_titles('rb_06_dec_13', 'rb_06_dec_12', 'rb_06_dec_11',
                'rb_06_dec_08', 'rb_06_dec_07')
        date = self.channel.items[0].date
        self.assertEquals(date.year, 2006)
        self.assertEquals(date.month, 12)
        self.assertEquals(date.day, 13)
        self.assertEquals(date.hour, 13)
        self.assertEquals(date.minute, 44)
        self.assertEquals(self.channel.items[0].guid,
                'http://www.rocketboom.com'
                '/vlog/archives/2006/12/rb_06_dec_13.html')
        self.assertEquals(self.channel.state, 'N')

    def test_parse_url(self):
        self.channel = self.make_channel(keep_download=True)
        self.channel.url = test_data_path('feed.xml') # feedparser doesn't care
                                                      # it's not a URL
        self.channel.update_items(self.connection)
        self.check_item_titles('rb_06_dec_13', 'rb_06_dec_12', 'rb_06_dec_11',
                'rb_06_dec_08', 'rb_06_dec_07')
        date = self.channel.items[0].date
        self.assertEquals(date.year, 2006)
        self.assertEquals(date.month, 12)
        self.assertEquals(date.day, 13)
        self.assertEquals(date.hour, 13)
        self.assertEquals(date.minute, 44)
        self.assertEquals(self.channel.items[0].guid,
                'http://www.rocketboom.com'
                '/vlog/archives/2006/12/rb_06_dec_13.html')
        self.assertEquals(self.channel.state, 'N')

    def test_duplicates_not_replaced(self):
        """Test that when we update a feed, we only replace thumbnails if
        the enclosure URL is different and the GUID is different.
        """
        def get_item_ids():
            query = Channel.query_with_items(id=self.channel.id)
            channel = query.get(self.connection)
            return [item.id for item in channel.items]
        self.channel.update_items(self.connection,
                feedparser_input=open(test_data_path('feed.xml')))
        old_ids = get_item_ids()
        self.channel.update_items(self.connection,
                feedparser_input=open(test_data_path('feed-future.xml')))
        # 2 new entries, 2 entries are gone, the rest are the same.  The new
        # feed has some entries where the GUID stays the same and some where
        # the enclosure URL stays the same It also has 2 entries with the same
        # enclosure URL to try to mess with the CG logic
        new_ids = get_item_ids()
        self.assert_(new_ids[0] not in old_ids)
        self.assert_(new_ids[1] not in old_ids)
        self.assert_(old_ids[-1] not in new_ids)
        self.assert_(old_ids[-2] not in new_ids)
        self.assertEquals(new_ids[2:], old_ids[0:-2])

    def test_date_is_updated(self):
        """
        If the date is updated in a feed item, the date should be updated in
        our database as well.
        """
        self.channel.update_items(self.connection,
                feedparser_input=open(test_data_path('feed-future.xml')))
        old_item = Item.query(name='rb_06_dec_12').get(self.connection)
        self.channel.update_items(self.connection,
                feedparser_input=open(test_data_path('feed-future-corner-cases.xml')))
        new_item = self.refresh_record(old_item)
        self.assertNotEquals(old_item.date, new_item.date)

    def test_future_corner_cases(self):
        """Test some corner cases when we update a feed, duplicate URLS,
        duplicate GUIDs, items missing GUIDs and URLS.
        """
        self.channel.update_items(self.connection,
                feedparser_input=open(test_data_path('feed-future.xml')))
        self.channel.update_items(self.connection,
                feedparser_input=open(test_data_path('feed-future-corner-cases.xml')))
        # Maybe we should test the behaviour here, but the main thing is the
        # guide shouldn't crash

    def test_do_not_require_enclosure_type(self):
        """
        Enclosures should not require a 'type' attribute.
        """
        entry = {'title': 'title',
                 'description': 'description',
                 'enclosures': [{'href': 'http://www.getmiro.com/video.flv'}]}
        i = Item.from_feedparser_entry(entry)
        self.assertEquals(i.name, 'title')
        self.assertEquals(i.description, 'description')
        self.assertEquals(i.url, 'http://www.getmiro.com/video.flv')
        self.assertEquals(i.mime_type, 'video/unknown')

    def test_media_description(self):
        """
        'media_description' should be tried as a fallback if 'description'
        isn't available.
        """
        entry = { 'title': 'title',
                  'media_description': 'description',
                  'enclosures': [{'href': 'http://www.getmiro.com/video.flv'}]}
        i = Item.from_feedparser_entry(entry)
        self.assertEquals(i.description, 'description')

    def test_thumbnails(self):
        width, height = Item.THUMBNAIL_SIZES[0]
        dir = '%dx%d' % (width, height)
        self.channel.update_items(self.connection,
                feedparser_input=open(test_data_path('thumbnails.xml')))
        self.channel.download_item_thumbnails(self.connection)
        self.assertEquals(self.channel.items[0].thumbnail_url,
                "http://www.getmiro.com/images/"
                "x11-front-page-screenshots/02.jpg")
        thumb_path = os.path.join(settings.MEDIA_ROOT, Item.THUMBNAIL_DIR,
                dir, '%d.jpeg' % self.channel.items[0].id)
        cache_path = os.path.join(settings.IMAGE_DOWNLOAD_CACHE_DIR,
                util.hash_string(self.channel.items[0].thumbnail_url))
        self.assert_(os.path.exists(thumb_path))
        self.assert_(os.path.exists(cache_path))
        self.assert_(self.channel.items[0].thumbnail_exists())
        self.assert_(not self.channel.items[1].thumbnail_exists())
        self.assertEquals(self.channel.items[1].thumb_url(width, height),
                self.channel.thumb_url(width, height))

    def test_item_info(self):
        def check_count(correct):
            channel = Channel.get(self.connection, self.channel.id,
                    load='item_count')
            self.assertEquals(channel.item_count, correct)
        check_count(0)
        self.channel.update_items(self.connection,
                feedparser_input=open(test_data_path('feed.xml')))
        check_count(5)

    def test_suspending_invalid_feed(self):
        """
        Invalid feeds should be marked as suspended when updated.
        """
        self.channel.update_items(self.connection,
                                  feedparser_input=open(test_data_path('badfeed.html')))
        self.update_channel()
        self.assertEquals(self.channel.state, Channel.SUSPENDED)

    def test_suspending_empty_feed(self):
        """
        Empty feeds (no items) should be marked as suspended when updated.
        """
        self.channel.update_items(self.connection,
                                  feedparser_input=open(test_data_path('emptyfeed.xml')))
        self.update_channel()
        self.assertEquals(self.channel.state, Channel.SUSPENDED)

    def test_unsuspending_feed(self):
        """
        If a formerly suspended feed is updated and works, it should return to
        its old state.
        """
        self.assertEquals(self.channel.state, Channel.NEW)
        self.channel.update_items(self.connection,
                                  feedparser_input=open(test_data_path('badfeed.html')))
        self.update_channel()
        self.assertEquals(self.channel.state, Channel.SUSPENDED)
        self.channel.update_items(self.connection,
                                  feedparser_input=open(test_data_path('feed.xml')))
        self.assertEquals(self.channel.state, Channel.NEW)

    def test_unsuspending_approved_feed(self):
        """
        If a suspended feed was previously approved, it should be approved
        again after suspension.
        """
        self.channel.change_state(self.ralph, Channel.APPROVED, self.connection)
        self.update_channel()
        old_approved_at = self.channel.approved_at
        self.channel.update_items(self.connection,
                                  feedparser_input=open(test_data_path('badfeed.html')))
        self.update_channel()
        self.assertEquals(self.channel.state, Channel.SUSPENDED)
        self.channel.update_items(self.connection,
                                  feedparser_input=open(test_data_path('feed.xml')))
        self.update_channel()
        self.assertEquals(self.channel.state, Channel.APPROVED)
        self.assertEquals(self.channel.approved_at, old_approved_at)
        self.assertEquals(self.channel.last_moderated_by_id, self.ralph.id)
        self.channel.join('moderator_actions').execute(self.connection)
        self.assertEquals(self.channel.moderator_actions[-1].user_id, self.ralph.id)
        self.assertEquals(self.channel.moderator_actions[-1].action, Channel.APPROVED)
        self.assertEquals(len(self.emails), 1) # one for the first approval

    def test_suspend_is_logged_invalid_feed(self):
        """
        Suspending an invalid feed should be logged as a moderator action.
        """
        self.channel.update_items(self.connection,
                                  feedparser_input=open(test_data_path('badfeed.html')))
        self.channel = self.refresh_record(self.channel)
        self.channel.join('moderator_actions').execute(self.connection)
        self.assertEquals(self.channel.moderator_actions[-1].action, Channel.SUSPENDED)

    def test_suspend_is_logged_empty(self):
        """
        Suspending an empty feed should be logged as a moderator action.
        """
        self.channel.update_items(self.connection,
                                  feedparser_input=open(test_data_path('emptyfeed.xml')))
        self.channel = self.refresh_record(self.channel)
        self.channel.join('moderator_actions').execute(self.connection)
        self.assertEquals(self.channel.moderator_actions[-1].action, Channel.SUSPENDED)

    def test_suspend_only_once(self):
        """
        A second update_items() call (say, the next evening) should not result
        in a second moderator action.
        """
        self.channel.update_items(self.connection,
                                  feedparser_input=open(test_data_path('badfeed.html')))
        self.channel.update_items(self.connection,
                                  feedparser_input=open(test_data_path('badfeed.html')))
        self.channel = self.refresh_record(self.channel)
        self.channel.join('moderator_actions').execute(self.connection)
        self.assertEquals(len(self.channel.moderator_actions), 1)
        self.assertEquals(self.channel.moderator_actions[-1].action, Channel.SUSPENDED)

    def test_suspend_only_once_when_download_returns_None(self):
        """
        A second update_items() call (say, the next evening) should not result
        in a second moderator action, even when download_feed() returns None
        """
        self.channel.update_items(self.connection,
                                  feedparser_input=open(test_data_path('badfeed.html')))
        download_feed = self.channel.download_feed
        self.channel.update_items(self.connection)
        self.channel = self.refresh_record(self.channel)
        self.channel.join('moderator_actions').execute(self.connection)
        self.assertEquals(len(self.channel.moderator_actions), 1)
        self.assertEquals(self.channel.moderator_actions[-1].action, Channel.SUSPENDED)

    def test_clean_out_old_suspensions_new(self):
        """
        If, due to a bug, there's a long line of suspensions on a good feed,
        they shouldn't be counted when going back to the previous state.
        """
        miroguide = User.query(username='miroguide').get(self.connection)
        for i in range(5):
            ModeratorAction(miroguide, self.channel, 'S').save(self.connection)
        self.update_channel()
        self.channel.update_items(self.connection,
                                  feedparser_input=open(test_data_path('badfeed.html')))
        self.channel.update_items(self.connection,
                                  feedparser_input=open(test_data_path('feed.xml')))
        self.update_channel()
        self.channel.join('moderator_actions').execute(self.connection)
        self.assertEquals(self.channel.state, 'N')
        self.assertEquals(self.channel.last_moderated_by_id, None)
        self.assertEquals(len(self.channel.moderator_actions), 0)


    def test_clean_out_old_suspensions_approved(self):
        """
        If, due to a bug, there's a long line of suspensions on a good feed,
        they shouldn't be counted when going back to the previous state.
        """
        self.channel.change_state(self.ralph, Channel.DONT_KNOW, self.connection)
        self.channel.change_state(self.ralph, Channel.APPROVED, self.connection)
        miroguide = User.query(username='miroguide').get(self.connection)
        for i in range(5):
            ModeratorAction(miroguide, self.channel, 'S').save(self.connection)
        self.update_channel()
        self.channel.update_items(self.connection,
                                  feedparser_input=open(test_data_path('badfeed.html')))
        self.channel.update_items(self.connection,
                                  feedparser_input=open(test_data_path('feed.xml')))
        self.update_channel()
        self.channel.join('moderator_actions').execute(self.connection)
        self.assertEquals(self.channel.state, 'A')
        self.assertEquals(self.channel.last_moderated_by_id, self.ralph.id)
        self.assertEquals(len(self.channel.moderator_actions), 2)

    def test_unmodified_suspended_with_items_are_unsuspended(self):
        """
        """
        self.channel.change_state(self.ralph, Channel.APPROVED, self.connection)
        self.channel.update_items(self.connection,
                                  feedparser_input=open(test_data_path('feed.xml')))
        self.update_channel()
        self.channel.change_state(self.ralph, Channel.SUSPENDED, self.connection)
        self.channel.download_feed = lambda: None
        self.channel.update_items(self.connection)
        self.assertEquals(self.channel.state, Channel.APPROVED)

    def test_URLError_does_not_cause_suspension(self):
        """
        An error on the Miroguide end (a URLError) shouldn't cause the channel
        to be suspended.
        """
        class MockFile:
            def read(self):
                raise URLError('error opening URL')

        self.channel.update_items(self.connection,
                                  feedparser_input=MockFile())
        self.assertEquals(self.channel.state, Channel.NEW)

    def test_good_feeds_not_suspended(self):
        """
        Test that some known-good feeds aren't marked as suspended.
        """
        self.channel.change_state(self.ralph, Channel.APPROVED, self.connection)
        self.update_channel()
        names = ['casthduk.xml', 'tagesschau.xml', 'feedMOV480.xml', 'thisrevolution.xml',
                 'angeklickt.xml', 'animax.xml']
        for name in names:
            feed_file = open(test_data_path(os.path.join('good', name)))
            self.channel.update_items(self.connection,
                                      feedparser_input=feed_file)
            self.update_channel()
            self.assertEquals(self.channel.state, Channel.APPROVED,
                              'suspended %r by mistake' % name)

    def test_bad_feeds_are_suspended(self):
        """
        Test that some known-bad feeds are marked as suspended.
        """
        names = ['24x7_podcasts.xml']
        for name in names:
            self.channel.change_state(self.ralph, Channel.APPROVED, self.connection)
            self.update_channel()
            feed_file = open(test_data_path(os.path.join('bad', name)))
            self.channel.update_items(self.connection,
                                      feedparser_input=feed_file)
            self.update_channel()
            self.assertEquals(self.channel.state, Channel.SUSPENDED,
                              'did not suspend %r by mistake' % name)

class SubmitChannelTest(TestCase):
    """Test the channel submit web pages."""

    def setUp(self):
        TestCase.setUp(self)
        self.joe = self.make_user('joe')
        self.cat1 = Category(name='foo')
        self.cat2 = Category(name='bar')
        self.save_to_db(self.cat1, self.cat2)

    def login(self):
        TestCase.login(self, 'joe')
        return self.get_page('/submit/step1')

    def test_login_required(self):
        response = self.get_page('/submit/step1')
        self.assertEquals(response.status_code, 302)
        response = self.get_page('/submit/step2')
        self.assertEquals(response.status_code, 302)

    def make_submit_data(self, dont_send=None, **extra_data):
        data = {
            'name': 'foo',
            'url': test_data_url('feed.xml'),
            'website_url': 'http://foo.com/' + util.random_string(16),
            'description': 'Awesome channel',
            'publisher': 'publisher@foo.com',
            'language': self.language.id,
            'categories_0': self.cat1.id,
            'categories_1': self.cat2.id,
            'thumbnail_file': open(test_data_path('thumbnail.jpg')),
            'thumbnail_file_submitted_path': '',
            'adult': False,
        }
        if isinstance(dont_send, list):
            for key in dont_send:
                del data[key]
        elif dont_send is not None:
            del data[dont_send]
        for key, value in extra_data.items():
            data[key] = value
        return data

    def get_last_channel(self):
        self.connection.commit()
        query = Channel.query().order_by('id', desc=True).limit(1)
        channel = query.get(self.connection)
        join = channel.join('items', 'tags', 'categories', 'owner', 'language')
        join.execute(self.connection)
        return channel

    def delete_last_channel(self):
        self.get_last_channel().delete(self.connection)
        self.connection.commit()

    def check_last_channel_thumbnail(self, thumb_name):
        last = self.get_last_channel()
        path = os.path.join(settings.MEDIA_ROOT, Channel.THUMBNAIL_DIR,
                'original', '%d.%s' % (last.id, last.thumbnail_extension))
        self.assert_(os.path.exists(path))
        right_data = util.read_file(test_data_path(thumb_name))
        actual_data = util.read_file(path)
        self.assert_(right_data == actual_data)

    def check_submit_url_failed(self, response):
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.template[0].name, 'guide/submit-feed-url.html')

    def check_submit_url_worked(self, response):
        self.assertEquals(response.status_code, 302)
        test_url = settings.BASE_URL_FULL + 'channels/submit/step2'
        self.assertEquals(response['Location'], test_url)

    def check_submit_failed(self, response):
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.template[0].name, 'guide/submit-channel.html')

    def check_submit_worked(self, response, url=None,
            thumb_name='thumbnail.jpg'):
        """
        Check that submitting the channel did not cause an error, and that
        it correctly redirected the user to the after submit page.
        """
        if response.status_code != 200:
            try:
                errors = response.context[0]['form'].errors.items()
            except:
                errors = "Unknown"
            msg = """\
Submit failed!
Status code: %s
Errors: %s""" % (response.status_code, errors)
            raise AssertionError(msg)
        self.assertEquals(response.content, 'SUBMIT SUCCESS')
        self.check_last_channel_thumbnail(thumb_name)
        return response

    def submit_url(self, url=None):
        if url is None:
            url = test_data_url('feed.xml')
        if url is '':
            # this used to be an error, because URLs were required
            # now they aren't, so we use a fake URL instead
            url = test_data_url('thisdoesntexist.xml')
        return self.post_data('/submit/step1', {
            'name': 'foo',
            'url': url})

    def login_and_submit_url(self):
        self.login()
        self.submit_url()

    def submit(self, old_response=None, dont_send=None, **extra_data):
        data = self.make_submit_data(dont_send=dont_send, **extra_data)
        if old_response:
            form = old_response.context[0]['form']
            thumb_widget = form.fields['thumbnail_file'].widget
            if thumb_widget.submitted_thumb_path is not None:
                data['thumbnail_file_submitted_path'] = \
                        thumb_widget.submitted_thumb_path
        return self.post_data('/submit/step2', data)

    def test_required_fields(self):
        self.login()
        response = self.post_data('/submit/step1', {})
        form = response.context[0]['form']
        self.assertEquals(form.errors.keys(), ['url', 'name'])
        self.submit_url(test_data_url('no-thumbnail.xml'))
        should_complain = ['name', 'url', 'website_url',
                'description', 'language','categories',
                'thumbnail_file']
        response = self.post_data('/submit/step2', {})
        form = response.context[0]['form']
        self.assertSameSet(form.errors.keys(), should_complain)

    def test_step2_redirect(self):
        self.login()
        response = self.get_page('/submit/step2')
        self.assertEquals(response.status_code, 302)

    def test_bad_url(self):
        self.login()
        response = self.submit_url('')
        self.check_submit_url_failed(response)
        response = self.submit_url(test_data_url('badfeed.html'))
        self.check_submit_url_failed(response)

    def test_submit_url_sets_defaults(self):
        self.login_and_submit_url()
        response = self.get_page('/submit/step2')
        form = response.context[0]['form']
        def check_default(key, test_value):
            self.assertEquals(form.fields[key].initial, test_value)
        check_default('name', 'Rocketboom RSS 2.0 Main Index')
        check_default('website_url', 'http://www.rocketboom.com/vlog/')
        check_default('publisher', self.joe.email)
        thumb_widget = form.fields['thumbnail_file'].widget
        self.assert_(thumb_widget.submitted_thumb_path is not None)
        self.assert_(os.path.exists(os.path.join(settings.MEDIA_ROOT, 'tmp',
            thumb_widget.submitted_thumb_path)))

    def test_submit(self):
        self.login_and_submit_url()
        response = self.submit()
        self.check_submit_worked(response)
        stored_url = self.get_last_channel().url
        self.assertEquals(stored_url, test_data_url('feed.xml'))

    def check_submitted_language(self, language):
        channel = self.get_last_channel()
        self.assertEquals(channel.language.id, language.id)

    def test_languages(self):
        self.login_and_submit_url()
        language1 = Language("french")
        language2 = Language("fooese")
        language3 = Language("barwegian")
        self.save_to_db(language1, language2, language3)
        response = self.submit(language=language1.id)
        self.check_submit_worked(response)
        self.check_submitted_language(language1)
        self.delete_last_channel()
        self.login_and_submit_url()
        response = self.submit(language=language3.id)
        self.check_submit_worked(response)
        self.check_submitted_language(language3)

    def test_remembers_thumbnail(self):
        self.login_and_submit_url()
        response = self.submit(dont_send='name')
        self.check_submit_failed(response)
        response = self.submit(response, dont_send='thumbnail_file')
        self.check_submit_worked(response)

    def test_replace_thumbnail(self):
        self.login_and_submit_url()
        response = self.submit(dont_send='name')
        self.check_submit_failed(response)
        response = self.submit(response,
                thumbnail_file=open(test_data_path('thumbnail_square.png')))
        self.check_submit_worked(response, thumb_name='thumbnail_square.png')

    def test_replace_and_remember_thumbnail(self):
        self.login_and_submit_url()
        response = self.submit(dont_send='name')
        self.check_submit_failed(response)
        response = self.submit(response, dont_send='name',
                thumbnail_file=open(test_data_path('thumbnail_square.png')))
        response = self.submit(response, dont_send='thumbnail_file')
        self.check_submit_worked(response, thumb_name='thumbnail_square.png')

    def test_thumbnails_converted_to_jpeg(self):
        self.login_and_submit_url()
        response = self.submit(thumbnail_file=
                               open(test_data_path('thumbnail_square.png')))
        channel = self.get_last_channel()
        self.assertTrue(channel.thumbnail_exists())
        for size in channel.THUMBNAIL_SIZES:
            path = channel.thumb_path('%dx%d' % size)
            self.assertTrue(os.path.exists(path))
            self.assertEquals(os.path.splitext(path)[1], '.jpeg')
            self.assertEquals(util.get_image_extension(
                    file(path).read()), 'jpeg')


    def test_submit_destroys_feed(self):
        self.login_and_submit_url()
        response = self.submit()
        self.check_submit_worked(response)
        response = self.get_page('/submit/step2')
        self.assertEquals(response.status_code, 302)

    def test_submit_feed_then_go_back(self):
        self.login_and_submit_url()
        response = self.submit_url('')
        self.check_submit_url_failed(response)
        response = self.get_page('/submit/step2')
        self.assertEquals(response.status_code, 302)

    def check_category_names(self, response, *correct_names):
        form = response.context[0]['form']
        names = [c[1] for c in form.fields['categories'].fields[0].choices]
        self.assertSameSet(names, list(correct_names) + ['<none>'])

    def test_categories_widget_updates(self):
        self.login_and_submit_url()
        response = self.get_page('/submit/step2')
        self.check_category_names(response, 'foo', 'bar')
        self.save_to_db(Category(name='baz'))
        response = self.get_page('/submit/step2')
        self.check_category_names(response, 'foo', 'bar', 'baz')
        self.save_to_db(Category(name='booya'))
        response = self.submit(dont_send='name')
        self.check_category_names(response, 'foo', 'bar', 'baz', 'booya')

    def test_tags(self):
        self.login_and_submit_url()
        response = self.submit(tags=' foo, bar  , booya ')
        last = self.get_last_channel()
        current_tags = [tag.name for tag in last.tags]
        self.assertSameSet(current_tags, ['foo', 'bar', 'booya'])

    def test_tag_bad_unicode(self):
        self.login_and_submit_url()
        response = self.submit(tags='\xff')
        last = self.get_last_channel()
        for tag in last.tags:
            self.assert_(isinstance(tag.name, unicode))
#            tag.name.decode('utf8')

    def test_no_tags(self):
        self.login_and_submit_url()
        response = self.submit()
        last = self.get_last_channel()
        self.assertSameSet(last.tags, [])

    def test_duplicate_category(self):
        self.login_and_submit_url()
        response = self.submit(categories_0=self.cat1.id,
                categories_1=self.cat2.id,
                categories_2=self.cat1.id)
        self.check_submit_worked(response)
        last = self.get_last_channel()
        category_ids = [c.id for c in last.categories]
        self.assertSameSet(category_ids, [self.cat1.id, self.cat2.id])

    def test_tag_limit(self):
        self.login_and_submit_url()
        response = self.submit(tags=','.join([str(i) for i in range(76)]))
        self.check_submit_failed(response)

    def test_empty_tag(self):
        def check_tags(tags, correct_tags):
            response = self.login_and_submit_url()
            response = self.submit(tags=tags)
            self.check_submit_worked(response)
            self.refresh_connection()
            last = self.get_last_channel()
            self.assertEquals(len(last.tags), len(correct_tags))
            for i in range(len(correct_tags)):
                self.assertEquals(last.tags[i].name, correct_tags[i])
        check_tags('a,  ,b', ['a', 'b'])
        self.delete_last_channel()
        check_tags('a,  ,b, , c,', ['a', 'b', 'c'])

    def test_url_unique(self):
        channel = self.make_channel(self.joe)
        self.login_and_submit_url()
        response = self.submit_url(channel.url)
        channel2 = response.context[0]['channel']
        self.assertEquals(channel.id, channel2.id)

    def test_website_url_not_unique_for_feed(self):
        channel = self.make_channel(self.joe)
        self.login_and_submit_url()
        response = self.submit(website_url=channel.website_url)
        self.check_submit_worked(response)

    def test_website_url_unique_for_site(self):
        channel = self.make_channel(self.joe)
        channel.url = None
        self.save_to_db(channel)
        mod = self.make_user('moderator', role=User.MODERATOR)
        TestCase.login(self, mod)
        self.post_data('/submit/step1', {'name': 'New Site'})
        response = self.submit(dont_send='url', website_url=channel.website_url)
        self.assertEquals(response.context[0]['form'].errors.keys(),
                          ['website_url'])
        # should work if the other channel is a feed
        channel.url = 'http://www.myblog.com/'
        self.save_to_db(channel)
        response = self.submit(dont_send='url', website_url=channel.website_url)
        self.check_submit_worked(response)

class ModerateChannelTest():
    """Test the moderate channel web page."""

    def setUp(self):
        ChannelTestBase.setUp(self)
        self.supermod = self.make_user('supermod', role=User.SUPERMODERATOR)
        self.joe = self.make_user('joe', role=User.MODERATOR)
        self.schmoe = self.make_user('schmoe')

    def login(self, username):
        ChannelTestBase.login(self, username)
        return self.get_page('/moderate')

    def test_moderator_required(self):
        response = self.get_page('/moderate')
        self.assertEquals(response.status_code, 302)
        response = self.login('schmoe')
        self.assertEquals(response.status_code, 302)
        response = self.login('joe')
        self.assertEquals(response.status_code, 200)

    def test_moderate_action(self):
        self.login('joe')
        def check_state(action, state):
            self.channel.state = Channel.NEW
            self.channel.url = None
            self.save_to_db(self.channel)
            url = self.channel.get_url()
            self.post_data(url, {'action': 'change-state', 'submit': action})
            self.connection.commit()
            updated = self.refresh_record(self.channel)
            self.assertEquals(updated.state, state)
        check_state('Approve', Channel.APPROVED)
        check_state("Don't Know", Channel.DONT_KNOW)

    def test_approve_without_owner_email(self):
        self.channel.owner.email = None
        self.save_to_db(self.channel.owner)
        self.channel.url = None
        self.save_to_db(self.channel)
        self.login('joe')
        url = self.channel.get_url()
        self.pause_logging()
        page = self.post_data(url, {'action': 'change-state', 'submit':
            'Approve'})
        self.check_logging(warnings=1)
        self.resume_logging()
        self.assertEquals(len(self.emails), 0)

    def test_reject(self):
        self.login('joe')
        def check_rejection_button(action):
            self.channel.state = Channel.NEW
            self.save_to_db(self.channel)
            self.connection.commit()
            starting_email_count = len(self.emails)
            before = self.refresh_record(self.channel, 'notes')
            url = self.channel.get_url()
            self.post_data(url, {'action': 'standard-reject', 'submit': action})
            after = self.refresh_record(self.channel, 'notes')
            self.assertEquals(after.state, Channel.REJECTED)
            self.assertEquals(len(after.notes), len(before.notes) + 1)
            self.assertEquals(len(self.emails), starting_email_count + 1)
        check_rejection_button('Broken')
        check_rejection_button('Copyrighted')
        check_rejection_button('Explicit')
        check_rejection_button('No Media')

    def test_custom_reject(self):
        self.login('joe')
        body = 'CUSTOM BODY'
        url = self.channel.get_url()
        self.post_data(url, {'action': 'reject', 'body':
            body})
        updated = self.refresh_record(self.channel, 'notes')
        self.assertEquals(updated.state, Channel.REJECTED)
        self.assertEquals(len(updated.notes), 1)
        self.assertEquals(updated.notes[0].body, body)
        self.assertEquals(len(self.emails), 1)

    def test_custom_reject_needs_body(self):
        self.login('joe')
        url = self.channel.get_url()
        self.post_data(url, {'action': 'reject', 'body':
            ''})
        updated = self.refresh_record(self.channel, 'notes')
        self.assertEquals(updated.state, Channel.NEW)

    def test_approve_and_feature_email(self):
        self.channel.url = None
        self.save_to_db(self.channel)
        self.login('supermod')
        url = self.channel.get_url()
        self.post_data(url, {'action': 'email', 'type':'Approve & Feature',
            'body': 'body', 'email':'email@address.com'})
        updated = self.refresh_record(self.channel, 'featured_queue')
        self.assertEquals(updated.state, Channel.APPROVED)
        self.assertEquals(updated.featured_queue.state,
                updated.featured_queue.IN_QUEUE)
        self.assertEquals(len(self.emails), 2)

    def test_feature_email(self):
        self.login('supermod')
        url = self.channel.get_url()
        self.post_data(url, {'action': 'email', 'type':'Feature',
            'body': 'body', 'email':'email@address.com'})
        updated = self.refresh_record(self.channel, 'featured_queue')
        self.assertEquals(updated.state, Channel.NEW)
        self.assertEquals(updated.featured_queue.state,
                updated.featured_queue.IN_QUEUE)
        self.assertEquals(len(self.emails), 1)

class ChannelSearchTest(ChannelTestBase):
    def setUp(self):
        ChannelTestBase.setUp(self)
        self.channel.update_items(self.connection,
                feedparser_input=open(test_data_path('feed.xml')))
        self.channel.items.join("search_data").execute(self.connection)
        self.channel.name = "Rocketboom"
        self.channel.description = ("Daily with Joanne Colan "
                "(that's right... Joanne Colan")
        self.channel.update_search_data(self.connection)
        self.channel.state = Channel.APPROVED
        self.channel.save(self.connection)
        # make bogus channels so that the the fulltext indexes work
        for x in range(10):
            c = self.make_channel(state=Channel.APPROVED)
            c.update_search_data(self.connection)

    def feed_search(self, query):
        page = self.get_page('/search', data={'query': query})
        return page.context[0]['feed_page'].object_list

    def feed_search_count(self, query):
        page = self.get_page('/search', data={'query': query})
        return page.context[0]['feed_page'].paginator.count

    def test_feed_search(self):
        results = [c.id for c in self.feed_search("Rocketboom")]
        self.assertEquals(results, [self.channel.id])
        self.assertEquals(self.feed_search_count("Rocketboom"), 1)
        self.assertSameSet(self.feed_search("Sprocketboom"), [])
        self.assertEquals(self.feed_search_count("Sprocketboom"), 0)

    def test_ordering(self):
        channel2 = self.make_channel(state=Channel.APPROVED)
        channel2.name = "Colan"
        channel2.save(self.connection)
        channel2.update_search_data(self.connection)
        self.connection.commit()
        # Having "Colan" in the title should trump "Colan" in the description
        results = self.feed_search("Colan")
        self.assertEquals(len(results), 2)
        self.assertEquals(results[0].name, channel2.name)
        self.assertEquals(results[1].name, self.channel.name)

    def make_unaprroved_channel(self):
        unapproved = self.make_channel()
        unapproved.name = "Unapproved"
        unapproved.update_search_data(self.connection)
        self.save_to_db(unapproved)
        return unapproved

    def test_unapproved_hidden(self):
        self.make_unaprroved_channel()
        self.assertEquals(self.feed_search_count('Unapproved'), 0)

    def test_mods_see_unapproved(self):
        unapproved = self.make_unaprroved_channel()
        self.login(self.make_user('reggie', role=User.MODERATOR))
        self.assertEquals(self.feed_search_count('Unapproved'), 1)

class EditChannelTest(ChannelTestBase):
    def setUp(self):
        ChannelTestBase.setUp(self)
        self.categories = {}
        self.languages = {}
        self.tags = {}
        self.make_category("arts")
        self.make_category("tech")
        self.make_category("comedy")
        self.make_language("piglatin")
        self.make_language("klingon")
        self.channel.categories.add_record(self.connection, self.categories['arts'])
        self.channel.categories.add_record(self.connection, self.categories['tech'])
        self.channel.add_tag(self.connection, self.ralph, u"funny\xfc")
        self.channel.add_tag(self.connection, self.ralph, "awesome")
        self.channel.url = test_data_url('feed.xml')
        self.channel.update_items(self.connection,
                feedparser_input=open(test_data_path('feed.xml')))
        self.save_to_db(self.channel)

    def make_category(self, name):
        cat = Category(name)
        self.categories[name] = cat
        self.save_to_db(cat)

    def make_language(self, name):
        language = Language(name)
        self.languages[name] = language
        self.save_to_db(language)

    def test_permissions(self):
        mod = self.make_user('jody', role=User.MODERATOR)
        other_user = self.make_user('bob')
        url = '%s/edit' % self.channel.get_url()
        self.check_page_access(mod, url, True)
        self.check_page_access(self.ralph, url, True)
        self.check_page_access(other_user, url, False)

    def post_to_edit_page(self, data):
        url = '%s/edit' % self.channel.get_url()
        return self.post_data(url, data)

    def test_change(self):
        self.login(self.ralph)
        self.assertFalse(self.channel.thumbnail_exists())
        data = {
                'url': self.channel.url,
                'categories_0': self.categories['arts'].id,
                'categories_1': self.categories['comedy'].id,
                'language': self.languages['klingon'].id,
                'tags': 'funny, cool, booya',
                'publisher': 'some@guy.com',
                'name': 'cool vids',
                'description': 'These are the best.',
                'website_url': 'http://www.google.com/',
                'thumbnail_file': open(test_data_path('thumbnail.jpg'))
        }

        self.post_to_edit_page(data)
        self.connection.commit()
        updated = self.refresh_record(self.channel, 'language', 'categories',
                'tags')
        self.assertEquals(updated.publisher, 'some@guy.com')
        self.assertEquals(updated.language.name, 'klingon')
        self.check_names(updated.categories, 'arts', 'comedy')
        self.check_names(updated.tags, 'funny', 'cool', 'booya')
        self.assertTrue(updated.thumbnail_exists())

    def get_default_values(self):
        data = {}
        for key in ['publisher', 'name',
                'website_url', 'description', 'url']:
            data[key] = getattr(self.channel, key)
        for i in xrange(len(self.channel.categories)):
            data['categories_%d' % i] = self.channel.categories[i].id
        data['tags'] = ', '.join(self.channel.tags)
        data['language'] = self.channel.language.id
        return data

    def test_empty_tags(self):
        self.login(self.ralph)
        data = self.get_default_values()
        data['tags'] = ''
        self.post_to_edit_page(data)
        self.connection.commit()
        updated = self.refresh_record(self.channel, 'tags')
        self.assertEquals(len(updated.tags), 0)

    def test_unicode(self):
        self.login(self.ralph)
        data = self.get_default_values()
        data['description'] = '\xd8\x8d\xd8\xa8\xd8\xa8\xd8\xa6\xd8\xb5'
        data['tags'] = 'Saxony, Sachsen, Th\xfcringen, Sachsen-Anhalt, MDR'
        self.post_to_edit_page(data)
        self.connection.commit()
        updated = self.refresh_record(self.channel, 'tags')

    def test_change_url(self):
        self.login(self.ralph)
        data = self.get_default_values()
        data['url'] = test_data_url('feed2.xml')
        url = '%s/edit' % self.channel.get_url()
        self.post_to_edit_page(data)
        self.connection.commit()
        updated = self.refresh_record(self.channel)
        self.assertEquals(updated.url, test_data_url('feed2.xml'))

    def check_names(self, name_list, *correct_names):
        names = [i.name for i in name_list]
        self.assertSameSet(names, correct_names)

    def test_edit_with_bad_url(self):
        # Give the channel a non-working URL and make sure we can still edit
        # the rest of the data.
        self.channel.url = 'http://pculture.org/badlink.php'
        self.save_to_db(self.channel)
        self.login(self.ralph)
        data = self.get_default_values()
        data['name'] = 'new name'
        self.post_to_edit_page(data)
        self.connection.commit()
        updated = self.refresh_record(self.channel)
        self.assertEquals(updated.name, 'new name')
        # but setting a new URL that doesn't work should fail
        data['url'] = 'http://pculture.org/badlink2.php'
        response = self.post_to_edit_page(data)
        self.assertEquals(response.status_code, 200)
        self.assert_(response.context[0]['form'].errors)

    def test_edit_thumbnail(self):
        self.login(self.ralph)
        data = self.get_default_values()
        data['thumbnail_file'] = open(test_data_path('thumbnail.jpg'))
        self.post_to_edit_page(data)
        self.connection.commit()
        updated = self.refresh_record(self.channel)
        self.assertTrue(updated.thumbnail_exists())

    def test_remembers_thumbnail(self):
        self.login(self.ralph)
        data = self.get_default_values()
        data['thumbnail_file'] = open(test_data_path('thumbnail.jpg'))
        del data['name']
        response = self.post_to_edit_page(data)
        self.connection.commit()
        updated = self.refresh_record(self.channel)
        self.assertFalse(updated.thumbnail_exists())

        data = self.get_default_values()
        data['thumbnail_file_submitted_path'] = response.context[0]['form'].fields['thumbnail_file'].widget.submitted_thumb_path
        self.post_to_edit_page(data)
        self.connection.commit()
        updated = self.refresh_record(self.channel)
        self.assertTrue(updated.thumbnail_exists())

class EmailChannelOwnersTest(TestCase):
    def test_permissions(self):
        super_mod = self.make_user('jody', role=User.SUPERMODERATOR)
        admin = self.make_user('rachel', role=User.ADMIN)
        url = '/channels/email-owners'
        self.check_page_access(super_mod, url, False)
        self.check_page_access(admin, url, True)

    def test_email(self):
        bob = self.make_user('bob')
        bonnie = self.make_user('bonnie')
        suzie = self.make_user('suzie')
        greg = self.make_user('greg')
        greg.channel_owner_emails = False
        self.save_to_db(greg)
        self.make_channel(bob, state=Channel.APPROVED)
        self.make_channel(bob, state=Channel.APPROVED)
        self.make_channel(suzie, state=Channel.APPROVED)
        self.make_channel(bonnie, state=Channel.REJECTED)
        self.make_channel(greg, state=Channel.APPROVED)
        admin = self.make_user('rachel', role=User.ADMIN)
        self.login(admin)
        data = {'body': 'email body', 'title': 'email_title'}
        self.post_data('/channels/email-owners', data)
        self.assertSameSet(self.email_recipients(), [bob.email, suzie.email])

class ChannelHTMLTest(ChannelTestBase):
    BAD_STRING = '<COOL &STUFF >HERE'

    def get_full_path(self):
        """
        Mock function to return a full HTTP path.
        """
        return settings.BASE_URL_FULL

    path = settings.BASE_URL_FULL

    def check_escaping(self):
        templates = [
            'show-channel.html',
        ]

        context = {'channel': self.channel, 'BASE_URL': settings.BASE_URL,
                   'request': self}

        for template in templates:
            html = loader.render_to_string(template, context)
            for bad_string in ('<COOL', '&STUFF', '>HERE'):
                if bad_string in html:
                    location = html.find(bad_string)
                    nearby_start = html.rfind('\n', 0, location-50)
                    nearby_end = html.find('\n', location+50)
                    nearby = html[nearby_start:nearby_end]
                    msg = "%s was found unquoted in %s\n: %s" % \
                        (bad_string, template, nearby)
                    raise AssertionError(msg)

    def test_escape_description(self):
        self.channel.description = self.BAD_STRING
        self.save_to_db(self.channel)
        self.check_escaping()

    def test_escape_name(self):
        self.channel.name = self.BAD_STRING
        self.save_to_db(self.channel)
        self.check_escaping()

    def test_escape_tags(self):
        self.channel.add_tag(self.connection, self.ralph, self.BAD_STRING)
        self.check_escaping()

    def test_escape_categories(self):
        category = Category(self.BAD_STRING)
        self.save_to_db(category)
        self.channel.categories.add_record(self.connection, category)
        self.check_escaping()

class ChannelCacheTest(ChannelTestBase):

    def setUp(self):
        ChannelTestBase.setUp(self)
        self.change_setting_for_test("DISABLE_CACHE", False)
        cache.clear_cache()
        time.sleep(1) # 1 sec granulaity in cache clearing
        self.regular = self.make_user('regular')
        self.regular.approved = 1
        self.save_to_db(self.regular)
        self.mod = self.make_user('mod', role='M')
        self.super = self.make_user('super', role='S')
        self.channel = self.make_channel(state='A')
        self.channel2 = self.make_channel(state='A')

    def get_renderings(self):
        url = self.channel.get_url()
        regular_render = self.get_page(url, login_as=self.regular).content
        mod_render = self.get_page(url, login_as=self.mod).content
        super_render = self.get_page(url, login_as=self.super).content
        owner_render = self.get_page(url, login_as=self.ralph).content
        return (regular_render, mod_render, super_render, owner_render)

    def test_channel_renders_differently_for_each_class(self):
        """
        The channel page should render differently for each class of user,
        regular, moderator, owner, and super-mod.
        """
        (regular_render, mod_render, super_render,
                owner_render) = self.get_renderings()
        self.failIfEqual(regular_render, mod_render)
        self.failIfEqual(regular_render, super_render)
        self.failIfEqual(regular_render, owner_render)
        self.failIfEqual(mod_render, super_render)
        self.failIfEqual(mod_render, owner_render)
        self.failIfEqual(super_render, owner_render)

    def test_rating_is_updated(self):
        """
        Changing a rating should update the rating part of the page.
        """
        (regular_render, mod_render, super_render,
                owner_render) = self.get_renderings()
        new_user = self.make_user('new')
        new_user.approved = 1
        self.save_to_db(new_user)
        self.get_page('%s/rate' % self.channel.get_url(),
                login_as=new_user, data={'rating': 5 })
        self.refresh_connection()
        (regular_rated, mod_rated, super_rated,
                owner_rated) = self.get_renderings()
        for render, rated in [
                (regular_render, regular_rated),
                (mod_render, mod_rated),
                (super_render, super_rated),
                (owner_render, owner_rated)]:
            self.failIfEqual(render, rated)
            self.failIfEqual(rated.find('Average Rating: 5'), -1)

    def test_rating_gives_user_rating(self):
        """
        If the user has rated a channel, it should give the user
        rating.  Otherwise, it should give the average rating.
        """
        self.get_page('%s/rate' % self.channel.get_url(),
                login_as=self.regular,
                data = {'rating': 5})
        self.refresh_connection()
        (regular_rated, mod_rated, super_rated,
                owner_rated) = self.get_renderings()
        self.failIfEqual(regular_rated.find('User Rating: 5'), -1)
        for rated in (mod_rated, super_rated, owner_rated):
            self.failIfEqual(rated.find('Average Rating: 5'), -1,
                    rated)

    def test_updating_channel_refreshes_page(self):
        """
        Changing the channel record should refresh the page.
        """
        url = self.channel.get_url()
        for user in (self.regular, self.mod, self.super, self.ralph):
            self.assert_(not hasattr(self.get_page(url, login_as=user),
                '_cache_hit'))
            self.assert_(hasattr(self.get_page(url, login_as=user),
                '_cache_hit'))
        (regular_render, mod_render, super_render,
                owner_render) = self.get_renderings()
        self.channel.description = 'Hello World!'
        self.save_to_db(self.channel)
        self.refresh_connection()
        for user in (self.regular, self.mod, self.super, self.ralph):
            self.assert_(not hasattr(self.get_page(url, login_as=user),
                '_cache_hit'))
            self.assert_(hasattr(self.get_page(url, login_as=user),
                '_cache_hit'))
        (regular_rated, mod_rated, super_rated,
                owner_rated) = self.get_renderings()
        for render, rated in [
                (regular_render, regular_rated),
                (mod_render, mod_rated),
                (super_render, super_rated),
                (owner_render, owner_rated)]:
            self.failIfEqual(render, rated)
            self.failIfEqual(rated.find('Hello World!'), -1)

    def test_changing_other_channel_doesnt_clear_cache(self):
        """
        Updating a different channel should not clear the cache for other
        channels.
        """
        url = self.channel.get_url()
        for user in (self.regular, self.mod, self.super, self.ralph):
            self.assert_(not hasattr(self.get_page(url, login_as=user),
                '_cache_hit'))
            self.assert_(hasattr(self.get_page(url, login_as=user),
                '_cache_hit'))
        self.channel2.description = 'Hello World!'
        self.save_to_db(self.channel2)
        self.refresh_connection()
        for user in (self.regular, self.mod, self.super, self.ralph):
            self.assert_(hasattr(self.get_page(url, login_as=user),
                '_cache_hit'), 'cache cleared for %s' % user.username)


class ChannelArchivalTest(ChannelTestBase):

    def test_archived(self):
        """
        If after a channel is updated, it hasn't had a new item in
        90 days, it should have its 'archived' flag set.
        """
        self.assertEquals(self.channel.archived, False)
        self.channel.update_items(self.connection,
                feedparser_input=open(test_data_path('feed.xml')))
        self.assertEquals(self.channel.archived, True)

        newer = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
<channel>
<title>Rocketboom RSS 2.0 Main Index</title>
<link>http://www.rocketboom.com/vlog/</link>
<item>
<title>Test</title>
<description>Test</description>
<link>Test</link>
<guid>Test</guid>
<pubDate>%s</pubDate>
<enclosure url="http://test.com/movie.mov" length="10000" type="video/quicktime"/>
</item>
</channel>
</rss>""" % datetime.now().strftime('%a,%e %h %Y %H:%M:%S %z')

        self.channel.update_items(self.connection, newer)
        self.assertEquals(self.channel.archived, False)

class AddedChannelTest(ChannelTestBase):

    def test_user_add(self):
        url = '%s/add' % self.channel.get_url()
        page = self.get_page(url, login_as=self.ralph)
        self.assertEquals(page.status_code, 200)
        self.refresh_connection()
        AddedChannel.get(self.connection, (self.channel.id,
                                              self.ralph.id))

    def test_nonuser_add(self):
        url = '%s/add' % self.channel.get_url()
        page = self.get_page(url, login_as=None)
        self.assertEquals(page.status_code, 200)

if settings.DISABLE_CACHE or not settings.MEMCACHED_SERVERS:
    del ChannelCacheTest
