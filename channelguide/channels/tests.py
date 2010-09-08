# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from datetime import datetime, timedelta
import os
import time
from urllib2 import URLError

from django.core import mail, management
from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib.auth.models import User
from django.template import loader

from channelguide import util
from channelguide.channels import views
from channelguide.channels.models import Channel, Item, AddedChannel
from channelguide.featured.models import FeaturedQueue, FeaturedEmail
from channelguide.labels.models import Category, Language, TagMap
from channelguide.moderate.models import ModeratorAction
from channelguide.ratings.models import GeneratedRatings
from channelguide.subscriptions.models import Subscription
from channelguide.testframework import TestCase, test_data_path, test_data_url

class ChannelTestBase(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.ralph = self.make_user('ralph')
        self.channel = self.make_channel()

    def make_channel(self, **kwargs):
        return TestCase.make_channel(self, self.ralph, **kwargs)

class ChannelModelTest(ChannelTestBase):
    """Test operations on the Channel class."""

    def get_thumb_path(self, subdir):
        file = "%d.jpeg" % self.channel.id
        return os.path.join(settings.MEDIA_ROOT, Channel.THUMBNAIL_DIR,
                subdir, file)

    def check_thumb_exists(self, subdir):
        self.assert_(os.path.exists(self.get_thumb_path(subdir)))

    def test_thumbnail(self):
        image_file = file(test_data_path('thumbnail.jpg'))
        self.channel.save_thumbnail(image_file)
        self.check_thumb_exists('original')
        for width, height in Channel.THUMBNAIL_SIZES:
            self.check_thumb_exists('%ix%i' % (width, height))
        self.assertEquals(image_file.read(),
                file(self.get_thumb_path('original')).read(),
                          'thumbnails are not equal')

    def test_approved_at(self):
        self.assertEquals(self.channel.approved_at, None)
        self.channel.change_state(self.ralph, Channel.APPROVED)
        timediff = datetime.now() - self.channel.approved_at
        self.assert_(timediff < timedelta(seconds=1))
        self.assert_(timediff > timedelta(seconds=0))
        self.channel.change_state(self.ralph, Channel.NEW)
        self.assertEquals(self.channel.approved_at, None)

    def test_approve_email(self):
        self.channel.change_state(self.ralph, Channel.APPROVED)
        self.assertEquals(len(mail.outbox), 1)
        self.assertEquals(mail.outbox[0].recipients(),
                [self.channel.owner.email])

    def test_approval_queue(self):
        self.assertEquals(Channel.objects.new().count(), 0)
        time.sleep(1)
        self.channel.change_state(self.ralph, Channel.APPROVED)
        time.sleep(1) # make sure they have different timestamps
        c2 = self.make_channel()
        c2.change_state(self.ralph, Channel.APPROVED)
        self.assertEquals(Channel.objects.new().count(), 0)
        management.call_command('update_new_channel_queue', verbosity=0)
        new_channels = Channel.objects.new()
        self.assertEquals(new_channels.count(), 1)
        self.assertEquals(new_channels[0].id, self.channel.id)
        management.call_command('update_new_channel_queue', verbosity=0)
        new_channels = Channel.objects.new()
        self.assertEquals(new_channels.count(), 2)
        self.assertEquals(new_channels[0].id, c2.id)

    def test_last_moderated_by(self):
        self.assertEquals(self.channel.last_moderated_by, None)
        self.channel.change_state(self.ralph, Channel.APPROVED)
        channel2 = Channel.objects.get(pk=self.channel.pk)
        self.assertEquals(channel2.last_moderated_by, self.ralph)

    def test_thumbnail_before_save(self):
        c = Channel()
        c.url = "http://myblog.com/videos/rss"
        c.website_url = "http://myblog.com/"
        c.publisher = "TestVision"
        c.description = "lots of stuff"
        self.assertRaises(ValueError, c.save_thumbnail,
                          file(test_data_path('thumbnail.jpg')))

    def check_tag_map_count(self, correct_count):
        tag_count = TagMap.objects.count()
        self.assertEquals(tag_count, correct_count)

    def test_delete(self):
        ben = self.make_user('ben')
        Subscription.objects.add(self.channel, '1.1.1.1')
        self.channel.add_tag(ben, 'cool')
        self.check_tag_map_count(1)
        self.channel.delete()
        self.check_tag_map_count(0)
        self.assertEquals(Subscription.objects.filter(
                channel=self.channel).count(),
                          0)

    def test_delete_user_with_tags(self):
        ben = self.make_user('ben')
        self.channel.add_tag(ben, 'cool')
        self.check_tag_map_count(1)
        ben.delete()
        self.check_tag_map_count(0)

    def test_category_counts(self):
        def test(cat, test_count):
            cat = Category.objects.get(pk=cat.id)
            self.assertEquals(cat.channels.filter(
                    state=Channel.APPROVED).count(), test_count)
        foo = Category(name='foo')
        bar = Category(name='bar')
        foo.save()
        bar.save()
        test(foo, 0)
        test(bar, 0)
        channel = self.make_channel(state=Channel.APPROVED)
        non_active = self.make_channel()
        channel.categories.add(foo)
        non_active.categories.add(bar)
        test(foo, 1)
        test(bar, 0)

    def test_featured_by(self):
        self.assertEquals(self.channel.featured_by, None)
        self.channel.change_featured(self.ralph)
        self.channel.save()
        channel2 = Channel.objects.get(pk=self.channel.pk)
        self.assertEquals(channel2.featured_by.id, self.ralph.id)
        channel2.change_featured(None)
        channel3 = Channel.objects.get(pk=self.channel.pk)
        self.assertEquals(channel3.featured_by, None)


class ChannelItemTest(ChannelTestBase):
    def check_item_titles(self, *correct_titles):
        items = self.channel.items.all()
        self.assertEquals(items.count(), len(correct_titles))
        for i in range(len(correct_titles)):
            self.assertEquals(items[i].name, correct_titles[i])

    def test_parse(self):
        self.channel.update_items(
            feedparser_input=open(test_data_path('feed.xml')))
        self.check_item_titles('rb_06_dec_13', 'rb_06_dec_12', 'rb_06_dec_11',
                'rb_06_dec_08', 'rb_06_dec_07')
        date = self.channel.items.all()[0].date
        self.assertEquals(date.year, 2006)
        self.assertEquals(date.month, 12)
        self.assertEquals(date.day, 13)
        self.assertEquals(date.hour, 13)
        self.assertEquals(date.minute, 44)
        self.assertEquals(self.channel.items.all()[0].guid,
                'http://www.rocketboom.com'
                '/vlog/archives/2006/12/rb_06_dec_13.html')
        self.assertEquals(self.channel.state, 'N')

    def test_parse_url(self):
        self.channel = self.make_channel(keep_download=True)
        self.channel.url = test_data_path('feed.xml') # feedparser doesn't care
                                                      # it's not a URL
        self.channel.update_items()
        self.check_item_titles('rb_06_dec_13', 'rb_06_dec_12', 'rb_06_dec_11',
                'rb_06_dec_08', 'rb_06_dec_07')
        date = self.channel.items.all()[0].date
        self.assertEquals(date.year, 2006)
        self.assertEquals(date.month, 12)
        self.assertEquals(date.day, 13)
        self.assertEquals(date.hour, 13)
        self.assertEquals(date.minute, 44)
        self.assertEquals(self.channel.items.all()[0].guid,
                'http://www.rocketboom.com'
                '/vlog/archives/2006/12/rb_06_dec_13.html')
        self.assertEquals(self.channel.state, 'N')

    def test_duplicates_not_replaced(self):
        """Test that when we update a feed, we only replace thumbnails if
        the enclosure URL is different and the GUID is different.
        """
        def get_item_ids():
            return list(self.channel.items.values_list('id', flat=True))
        self.channel.update_items(
            feedparser_input=open(test_data_path('feed.xml')))
        old_ids = get_item_ids()
        self.channel.update_items(
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
        self.channel.update_items(
            feedparser_input=open(test_data_path('feed-future.xml')))
        old_item = Item.objects.get(name='rb_06_dec_12')
        self.channel.update_items(
            feedparser_input=open(test_data_path(
                    'feed-future-corner-cases.xml')))
        new_item = Item.objects.get(pk=old_item.pk)
        self.assertNotEquals(old_item.date, new_item.date)

    def test_future_corner_cases(self):
        """Test some corner cases when we update a feed, duplicate URLS,
        duplicate GUIDs, items missing GUIDs and URLS.
        """
        self.channel.update_items(
            feedparser_input=open(test_data_path('feed-future.xml')))
        self.channel.update_items(
            feedparser_input=open(test_data_path(
                    'feed-future-corner-cases.xml')))
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
        self.channel.update_items(
            feedparser_input=open(test_data_path('thumbnails.xml')))
        self.channel.download_item_thumbnails()
        items = self.channel.items.all()
        self.assertEquals(items[0].thumbnail_url,
                "http://www.getmiro.com/images/"
                "x11-front-page-screenshots/02.jpg")
        thumb_path = os.path.join(settings.MEDIA_ROOT, Item.THUMBNAIL_DIR,
                dir, '%d.jpeg' % items[0].id)
        cache_path = os.path.join(settings.IMAGE_DOWNLOAD_CACHE_DIR,
                util.hash_string(items[0].thumbnail_url))
        self.assert_(os.path.exists(thumb_path))
        self.assert_(os.path.exists(cache_path))
        self.assert_(items[0].thumbnail_exists())
        self.assert_(not items[1].thumbnail_exists())
        self.assertEquals(items[1].thumb_url(width, height),
                self.channel.thumb_url(width, height))

    def test_item_info(self):
        def check_count(correct):
            channel = Channel.objects.get(pk=self.channel.id)
            self.assertEquals(channel.items.count(), correct)
        check_count(0)
        self.channel.update_items(
            feedparser_input=open(test_data_path('feed.xml')))
        check_count(5)


class ChannelSuspensionTest(ChannelTestBase):

    def update_channel(self):
        """
        Refresh the default channel and rejoin the items.  Useful for
        refreshing before update_items().
        """
        self.channel = Channel.objects.get(pk=self.channel.pk)

    def test_suspending_invalid_feed(self):
        """
        Invalid feeds should be marked as suspended when updated.
        """
        self.channel.update_items(
            feedparser_input=open(test_data_path('badfeed.html')))
        self.update_channel()
        self.assertEquals(self.channel.state, Channel.SUSPENDED)

    def test_suspending_empty_feed(self):
        """
        Empty feeds (no items) should be marked as suspended when updated.
        """
        self.channel.update_items(
            feedparser_input=open(test_data_path('emptyfeed.xml')))
        self.update_channel()
        self.assertEquals(self.channel.state, Channel.SUSPENDED)

    def test_unsuspending_feed(self):
        """
        If a formerly suspended feed is updated and works, it should return to
        its old state.
        """
        self.assertEquals(self.channel.state, Channel.NEW)
        self.channel.update_items(
            feedparser_input=open(test_data_path('badfeed.html')))
        self.update_channel()
        self.assertEquals(self.channel.state, Channel.SUSPENDED)
        self.channel.update_items(
            feedparser_input=open(test_data_path('feed.xml')))
        self.assertEquals(self.channel.state, Channel.NEW)

    def test_unsuspending_approved_feed(self):
        """
        If a suspended feed was previously approved, it should be approved
        again after suspension.
        """
        self.channel.change_state(self.ralph, Channel.APPROVED)
        old_approved_at = self.channel.approved_at.replace(microsecond=0)
        self.channel.update_items(
            feedparser_input=open(test_data_path('badfeed.html')))
        self.update_channel()
        self.assertEquals(self.channel.state, Channel.SUSPENDED)
        self.channel.update_items(
            feedparser_input=open(test_data_path('feed.xml')))
        self.update_channel()
        self.assertEquals(self.channel.state, Channel.APPROVED)
        self.assertEquals(self.channel.approved_at, old_approved_at)
        self.assertEquals(self.channel.last_moderated_by_id, self.ralph.id)
        self.assertEquals(self.channel.moderator_actions.all()[0].user_id,
                          self.ralph.id)
        self.assertEquals(self.channel.moderator_actions.all()[0].action,
                          Channel.APPROVED)
        self.assertEquals(len(mail.outbox), 1) # one for the first approval

    def test_suspend_is_logged_invalid_feed(self):
        """
        Suspending an invalid feed should be logged as a moderator action.
        """
        self.channel.update_items(
            feedparser_input=open(test_data_path('badfeed.html')))
        self.update_channel()
        self.assertEquals(self.channel.moderator_actions.all()[0].action,
                          Channel.SUSPENDED)

    def test_suspend_is_logged_empty(self):
        """
        Suspending an empty feed should be logged as a moderator action.
        """
        self.channel.update_items(
            feedparser_input=open(test_data_path('emptyfeed.xml')))
        self.update_channel()
        self.assertEquals(self.channel.moderator_actions.all()[0].action,
                          Channel.SUSPENDED)

    def test_suspend_only_once(self):
        """
        A second update_items() call (say, the next evening) should not result
        in a second moderator action.
        """
        self.channel.update_items(
            feedparser_input=open(test_data_path('badfeed.html')))
        self.channel.update_items(
            feedparser_input=open(test_data_path('badfeed.html')))
        self.update_channel()
        self.assertEquals(self.channel.moderator_actions.count(), 1)
        self.assertEquals(self.channel.moderator_actions.all()[0].action,
                          Channel.SUSPENDED)

    def test_suspend_only_once_when_download_returns_None(self):
        """
        A second update_items() call (say, the next evening) should not result
        in a second moderator action, even when download_feed() returns None
        """
        self.channel.update_items(
            feedparser_input=open(test_data_path('badfeed.html')))
        self.channel.update_items()
        self.update_channel()
        self.assertEquals(self.channel.moderator_actions.count(), 1)
        self.assertEquals(self.channel.moderator_actions.all()[0].action,
                          Channel.SUSPENDED)

    def test_clean_out_old_suspensions_new(self):
        """
        If, due to a bug, there's a long line of suspensions on a good feed,
        they shouldn't be counted when going back to the previous state.
        """
        miroguide = User.objects.get(username='miroguide')
        for i in range(5):
            ModeratorAction(user=miroguide, channel=self.channel,
                            action='S').save()
        self.update_channel()
        self.channel.update_items(
            feedparser_input=open(test_data_path('badfeed.html')))
        self.channel.update_items(
            feedparser_input=open(test_data_path('feed.xml')))
        self.update_channel()
        self.assertEquals(self.channel.state, 'N')
        self.assertEquals(self.channel.last_moderated_by_id, None)
        self.assertEquals(self.channel.moderator_actions.count(), 0)


    def test_clean_out_old_suspensions_approved(self):
        """
        If, due to a bug, there's a long line of suspensions on a good feed,
        they shouldn't be counted when going back to the previous state.
        """
        self.channel.change_state(self.ralph, Channel.DONT_KNOW)
        self.channel.change_state(self.ralph, Channel.APPROVED)
        miroguide = User.objects.get(username='miroguide')
        for i in range(5):
            ModeratorAction(user=miroguide, channel=self.channel,
                            action='S').save()
        self.update_channel()
        self.channel.update_items(
            feedparser_input=open(test_data_path('badfeed.html')))
        self.channel.update_items(
            feedparser_input=open(test_data_path('feed.xml')))
        self.update_channel()
        self.assertEquals(self.channel.state, 'A')
        self.assertEquals(self.channel.last_moderated_by_id, self.ralph.id)
        self.assertEquals(self.channel.moderator_actions.count(), 2)

    def test_unmodified_suspended_with_items_are_unsuspended(self):
        """
        """
        self.channel.change_state(self.ralph, Channel.APPROVED)
        self.channel.update_items(
            feedparser_input=open(test_data_path('feed.xml')))
        self.update_channel()
        self.channel.change_state(self.ralph, Channel.SUSPENDED)
        self.channel.download_feed = lambda: None
        self.channel.update_items()
        self.assertEquals(self.channel.state, Channel.APPROVED)

    def test_URLError_does_not_cause_suspension(self):
        """
        An error on the Miroguide end (a URLError) shouldn't cause the channel
        to be suspended.
        """
        class MockFile:
            def read(self):
                raise URLError('error opening URL')

        self.channel.update_items(
            feedparser_input=MockFile())
        self.assertEquals(self.channel.state, Channel.NEW)

    def test_good_feeds_not_suspended(self):
        """
        Test that some known-good feeds aren't marked as suspended.
        """
        self.channel.change_state(self.ralph, Channel.APPROVED)
        self.update_channel()
        names = ['casthduk.xml', 'tagesschau.xml', 'feedMOV480.xml',
                 'thisrevolution.xml',
                 'angeklickt.xml', 'animax.xml']
        for name in names:
            feed_file = open(test_data_path(os.path.join('good', name)))
            self.channel.update_items(
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
            self.channel.change_state(self.ralph, Channel.APPROVED)
            self.update_channel()
            feed_file = open(test_data_path(os.path.join('bad', name)))
            self.channel.update_items(
                feedparser_input=feed_file)
            self.update_channel()
            self.assertEquals(self.channel.state, Channel.SUSPENDED,
                              'did not suspend %r by mistake' % name)


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
        self.channel.categories.add(self.categories['arts'])
        self.channel.categories.add(self.categories['tech'])
        self.channel.add_tag(self.ralph, u"funny\xfc")
        self.channel.add_tag(self.ralph, "awesome")
        self.channel.url = test_data_url('feed.xml')
        self.channel.update_items(
                feedparser_input=open(test_data_path('feed.xml')))
        self.channel.save()

    def make_category(self, name):
        cat = Category(name=name)
        self.categories[name] = cat
        cat.save()

    def make_language(self, name):
        language = Language(name=name)
        self.languages[name] = language
        language.save()

    def test_permissions(self):
        mod = self.make_user('jody', group='cg_moderator')
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
        updated = Channel.objects.get(pk=self.channel.pk)
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
        for i in xrange(len(self.channel.categories.all())):
            data['categories_%d' % i] = self.channel.categories.all()[i].id
        data['tags'] = ', '.join([tag.name for tag in self.channel.tags.all()])
        data['language'] = self.channel.language.id
        return data

    def test_empty_tags(self):
        self.login(self.ralph)
        data = self.get_default_values()
        data['tags'] = ''
        self.post_to_edit_page(data)
        updated = Channel.objects.get(pk=self.channel.pk)
        self.assertEquals(updated.tags.count(), 0)

    def test_unicode(self):
        self.login(self.ralph)
        data = self.get_default_values()
        description = u'\u060d\u0628\u0628\u0626\u0635'
        tags = u'Saxony, Sachsen, Th\xfcringen, Sachsen-Anhalt, MDR'
        data['description'] = description.encode('utf8')
        data['tags'] = tags.encode('utf8')
        self.post_to_edit_page(data)
        updated = Channel.objects.get(pk=self.channel.pk)
        self.assertEquals(updated.description, description)
        self.check_names(updated.tags, *tags.split(', '))

    def test_change_url(self):
        self.login(self.ralph)
        data = self.get_default_values()
        data['url'] = test_data_url('feed2.xml')
        self.post_to_edit_page(data)
        updated = Channel.objects.get(pk=self.channel.pk)
        self.assertEquals(updated.url, test_data_url('feed2.xml'))

    def check_names(self, name_list, *correct_names):
        names = [i.name for i in name_list.all()]
        self.assertSameSet(names, correct_names)

    def test_edit_with_bad_url(self):
        # Give the channel a non-working URL and make sure we can still edit
        # the rest of the data.
        self.channel.url = 'http://pculture.org/badlink.php'
        self.channel.save()
        self.login(self.ralph)
        data = self.get_default_values()
        data['name'] = 'new name'
        self.post_to_edit_page(data)
        updated = Channel.objects.get(pk=self.channel.pk)
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
        updated = Channel.objects.get(pk=self.channel.pk)
        self.assertTrue(updated.thumbnail_exists())

    def test_remembers_thumbnail(self):
        self.login(self.ralph)
        data = self.get_default_values()
        data['thumbnail_file'] = open(test_data_path('thumbnail.jpg'))
        del data['name']
        response = self.post_to_edit_page(data)
        updated = Channel.objects.get(pk=self.channel.pk)
        self.assertFalse(updated.thumbnail_exists())

        data = self.get_default_values()
        widget = response.context[0]['form'].fields['thumbnail_file'].widget
        data['thumbnail_file_submitted_path'] = widget.submitted_thumb_path

        self.post_to_edit_page(data)
        updated = Channel.objects.get(pk=self.channel.pk)
        self.assertTrue(updated.thumbnail_exists())

    def test_change_owner(self):
        mod = self.make_user('mod', group='cg_moderator')
        supermod = self.make_user('super', group='cg_supermoderator')
        for user in self.ralph, mod:
            self.post_data(self.channel.get_url(),
                           {'action': 'change-owner',
                            'owner': mod.username}, login_as=user)
            self.assertEquals(Channel.objects.get(pk=self.channel.pk).owner,
                              self.ralph) # didn't change
        self.post_data(self.channel.get_url(),
                       {'action': 'change-owner',
                        'owner': mod.username}, login_as=supermod)
        self.assertEquals(Channel.objects.get(pk=self.channel.pk).owner,
                          mod) # didn't change

    def test_change_owner_changes_tag_owner(self):
        supermod = self.make_user('super', group='cg_supermoderator')
        old_names = [tag.name for tag in self.channel.get_tags_for_owner()]
        self.post_data(self.channel.get_url(),
                       {'action': 'change-owner',
                        'owner': supermod.username}, login_as=supermod)
        channel = Channel.objects.get(pk=self.channel.pk)
        self.assertEquals(set(tag.name for tag in
                              channel.get_tags_for_owner()),
                          set(old_names))

class EmailPopupTest(ChannelTestBase):
    def test_feature(self):
        supermod = self.make_user('super', group=['cg_moderator',
                                                  'cg_supermoderator'])
        url = reverse(views.email, args=(self.channel.pk,))
        page = self.get_page(url, login_as=supermod,
                             data={'type': 'Feature'})
        self.assertEquals(page.context['channel'], self.channel)
        self.assertEquals(page.context['type'], 'Feature')
        self.assertEquals(page.context['action'], 'feature')
        self.assertEquals(page.context['skipable'], True)

    def test_refeature(self):
        supermod = self.make_user('super', group=['cg_moderator',
                                                  'cg_supermoderator'])
        url = reverse(views.email, args=(self.channel.pk,))
        page = self.get_page(url, login_as=supermod,
                             data={'type': 'Refeature'})
        self.assertEquals(page.context['channel'], self.channel)
        self.assertEquals(page.context['type'], 'Refeature')
        self.assertEquals(page.context['action'], 'feature')
        self.assertEquals(page.context['skipable'], True)

    def test_approve_and_feature(self):
        supermod = self.make_user('super', group=['cg_moderator',
                                                  'cg_supermoderator'])
        url = reverse(views.email, args=(self.channel.pk,))
        page = self.get_page(url, login_as=supermod,
                             data={'type': 'Approve & Feature'})
        self.assertEquals(page.context['channel'], self.channel)
        self.assertEquals(page.context['type'], 'Approve & Feature')
        self.assertEquals(page.context['action'], 'change-state')
        self.assertEquals(page.context['skipable'], True)

    def test_custom(self):
        supermod = self.make_user('super', group=['cg_moderator',
                                                  'cg_supermoderator'])
        url = reverse(views.email, args=(self.channel.pk,))
        page = self.get_page(url, login_as=supermod,
                             data={'type': 'Custom'})
        self.assertEquals(page.context['channel'], self.channel)
        self.assertEquals(page.context['type'], 'Reject')
        self.assertEquals(page.context['action'], 'reject')
        self.assertEquals(page.context['body'], '')
        self.assertEquals(page.context['skipable'], False)

class EmailChannelOwnersTest(TestCase):
    def test_permissions(self):
        super_mod = self.make_user('jody', group=['cg_supermoderator'])
        admin = self.make_user('rachel')
        admin.is_superuser = True
        admin.save()
        url = '/channels/email-owners'
        self.check_page_access(super_mod, url, False)
        self.check_page_access(admin, url, True)

    def test_email(self):
        bob = self.make_user('bob')
        bonnie = self.make_user('bonnie')
        suzie = self.make_user('suzie')
        greg = self.make_user('greg')
        greg.get_profile().channel_owner_emails = False
        greg.get_profile().save()
        self.make_channel(bob, state=Channel.APPROVED)
        self.make_channel(bob, state=Channel.APPROVED)
        self.make_channel(suzie, state=Channel.APPROVED)
        self.make_channel(bonnie, state=Channel.REJECTED)
        self.make_channel(greg, state=Channel.APPROVED)
        admin = self.make_user('rachel')
        admin.is_superuser = True
        admin.save()
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
            'channels/show-channel.html',
        ]

        context = {'channel': self.channel, 'BASE_URL': settings.BASE_URL,
                   'user': self.ralph, 'request': self}

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
        self.channel.save()
        self.check_escaping()

    def test_escape_name(self):
        self.channel.name = self.BAD_STRING
        self.channel.save()
        self.check_escaping()

    def test_escape_tags(self):
        self.channel.add_tag(self.ralph, self.BAD_STRING)
        self.check_escaping()

    def test_escape_categories(self):
        category = Category(name=self.BAD_STRING)
        category.save()
        self.channel.categories.add(category)
        self.check_escaping()

class ChannelArchivalTest(ChannelTestBase):

    def test_archived(self):
        """
        If after a channel is updated, it hasn't had a new item in
        90 days, it should have its 'archived' flag set.
        """
        self.assertEquals(self.channel.archived, False)
        self.channel.update_items(
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
<enclosure url="http://test.com/movie.mov" length="10000"
           type="video/quicktime"/>
</item>
</channel>
</rss>""" % datetime.now().strftime('%a,%e %h %Y %H:%M:%S %z')

        self.channel.update_items(newer)
        self.assertEquals(self.channel.archived, False)


class ChannelViewTest(ChannelTestBase):
    def test_creates_generatedrating(self):
        self.assertEquals(
            GeneratedRatings.objects.filter(channel=self.channel).count(),
            0)
        self.get_page(self.channel.get_url())
        self.assertEquals(
            GeneratedRatings.objects.filter(channel=self.channel).count(),
            1)

    def test_show_doesnt_have_feature_email_form(self):
        mod = self.make_user('mod', group='cg_moderator')
        for user in None, self.ralph, mod:
            page = self.get_page(self.channel.get_url(),
                                 login_as=user)
            self.assertFalse('featured_email_form' in page.context[-1])
            self.assertFalse('last_featured_email' in page.context[-1])

    def test_supermod_show_has_feature_email_form(self):
        supermod = self.make_user('super', group=['cg_moderator',
                                                  'cg_supermoderator'])
        FeaturedQueue.objects.feature(self.channel, supermod)
        page = self.get_page(self.channel.get_url(), login_as=supermod)
        self.assertTrue(page.context['channel'].featured)
        self.assertTrue('featured_email_form' in page.context[-1])
        self.assertEquals(page.context[-1]['last_featured_email'], None)

    def test_supermod_show_with_featured_email(self):
        supermod = self.make_user('super', group=['cg_moderator',
                                                  'cg_supermoderator'])
        FeaturedQueue.objects.feature(self.channel, supermod)
        email = FeaturedEmail.objects.create(channel=self.channel,
                                             title='title',
                                             body='body',
                                             email=self.ralph.email,
                                             sender=supermod)
        page = self.get_page(self.channel.get_url(), login_as=supermod)
        self.assertTrue(page.context['channel'].featured)
        self.assertTrue('featured_email_form' in page.context[-1])
        self.assertEquals(page.context[-1]['last_featured_email'], email)

    def test_supermod_shows_last_email(self):
        supermod = self.make_user('super', group=['cg_moderator',
                                                  'cg_supermoderator'])
        FeaturedQueue.objects.feature(self.channel, supermod)
        FeaturedEmail.objects.create(channel=self.channel,
                                     title='title',
                                     body='body',
                                     email=self.ralph.email,
                                     sender=supermod)
        last_email = FeaturedEmail.objects.create(channel=self.channel,
                                                  title='title 2',
                                                  body='body 2',
                                                  email=self.ralph.email,
                                                  sender=supermod)

        page = self.get_page(self.channel.get_url(), login_as=supermod)
        self.assertTrue(page.context['channel'].featured)
        self.assertTrue('featured_email_form' in page.context[-1])
        self.assertEquals(page.context[-1]['last_featured_email'], last_email)

class AddedChannelTest(ChannelTestBase):

    def test_user_add(self):
        url = reverse(views.user_add, args=(self.channel.pk,))
        page = self.get_page(url, login_as=self.ralph)
        self.assertEquals(page.status_code, 200)
        AddedChannel.objects.get(channel=self.channel,
                                 user=self.ralph)

    def test_nonuser_add(self):
        url = reverse(views.user_add, args=(self.channel.pk,))
        page = self.get_page(url, login_as=None)
        self.assertEquals(page.status_code, 200)
        self.assertEquals(AddedChannel.objects.count(), 0)

    def test_view_subscriptions(self):
        AddedChannel.objects.get_or_create(user=self.ralph,
                                                channel=self.channel)
        url = reverse(views.user_subscriptions)
        response = self.get_page(url, login_as=self.ralph)
        self.assertEquals(response.context['feed_page'].paginator.count, 1)
        self.assertEquals(list(response.context['feed_page'].object_list),
                          [self.channel])
