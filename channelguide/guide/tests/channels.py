from datetime import datetime, timedelta
import cgi
import os
import time

from django.conf import settings
from django.template import loader

from channelguide import util, manage, cache
from channelguide.guide import search
from channelguide.guide.models import (Channel, Category, Tag, Item, User, 
        Language, TagMap, Rating)
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

    def check_thumb_size(self, subdir, width, height):
        i = Image.open(self.get_thumb_path(subdir))
        self.assertEquals(i.size, (width, height))

    def test_thumbnail(self):
        image_data = util.read_file(test_data_path('thumbnail.jpg'))
        self.channel.save_thumbnail(self.connection, image_data)
        self.check_thumb_exists('original')
        self.check_thumb_exists('60x40')
        self.check_thumb_exists('120x80')
        self.check_thumb_exists('252x169')
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
        c.short_description = "stuff"
        c.description = "lots of stuff"
        self.assertRaises(ValueError, c.save_thumbnail,
                self.connection, 
                util.read_file(test_data_path('thumbnail.jpg')))

    def check_subscription_counts(self, total, month, today):
        subscription_count_today = self.connection.execute('SELECT COUNT(*) FROM cg_channel_subscription WHERE channel_id=%s and timestamp>DATE_SUB(NOW(), INTERVAL 1 DAY)', self.channel.id)[0][0]
        subscription_count_month = self.connection.execute('SELECT COUNT(*) FROM cg_channel_subscription WHERE channel_id=%s and timestamp>DATE_SUB(NOW(), INTERVAL 1 MONTH)', self.channel.id)[0][0]
        subscription_count = self.connection.execute('SELECT COUNT(*) FROM cg_channel_subscription WHERE channel_id=%s', self.channel.id)[0][0]
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

    def test_thumbnails(self):
        width, height = Item.THUMBNAIL_SIZES[0]
        dir = '%dx%d' % (width, height)
        self.channel.update_items(self.connection,
                feedparser_input=open(test_data_path('thumbnails.xml')))
        self.channel.download_item_thumbnails(self.connection)
        self.assertEquals(self.channel.items[0].thumbnail_url,
                "http://www.getdemocracy.com/images/"
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
        return self.get_page('/channels/submit/step1')

    def test_login_required(self):
        response = self.get_page('/channels/submit/step1')
        self.assertEquals(response.status_code, 302)
        response = self.get_page('/channels/submit/step2')
        self.assertEquals(response.status_code, 302)

    def make_submit_data(self, dont_send=None, **extra_data):
        data = {
            'name': 'foo',
            'website_url': 'http://foo.com/' + util.random_string(16),
            'short_description': 'booya',
            'description': 'Awesome channel',
            'publisher': 'Foo incorporated',
            'language': self.language.id,
            'category1': self.cat1.id,
            'category2': self.cat2.id,
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
        join = channel.join('items', 'tags', 'categories', 'owner', 'language',
                'secondary_languages')
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
        if response.status_code != 302:
            try:
                errors = response.context[0]['form'].errors.items()
            except:
                errors = "Unknown"
            msg = """\
Submit failed!
Status code: %s
Errors: %s""" % (response.status_code, errors)
            raise AssertionError(msg)
        if url is None:
            url = test_data_url('feed.xml')
        test_url = settings.BASE_URL_FULL + 'channels/submit/after?%s' % url
        self.assertEquals(response['Location'], test_url)
        self.check_last_channel_thumbnail(thumb_name)

    def submit_url(self, url=None):
        if url is None:
            url = test_data_url('feed.xml')
        return self.post_data('/channels/submit/step1', {'url': url})

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
        return self.post_data('/channels/submit/step2', data)

    def test_required_fields(self):
        self.login()
        response = self.post_data('/channels/submit/step1', {})
        form = response.context[0]['form']
        self.assertEquals(form.errors.keys(), ['url'])
        self.submit_url()
        should_complain = ['name', 'website_url', 'short_description',
                'description', 'publisher', 'language','category1',
                'thumbnail_file']
        response = self.post_data('/channels/submit/step2', {})
        form = response.context[0]['form']
        self.assertSameSet(form.errors.keys(), should_complain)

    def test_step2_redirect(self):
        self.login()
        response = self.get_page('/channels/submit/step2')
        self.assertEquals(response.status_code, 302)

    def test_submit_url(self):
        self.login()
        response = self.submit_url()
        self.check_submit_url_worked(response)

    def test_submit_without_thumbnail(self):
        self.login()
        response = self.submit_url(test_data_url('no-thumbnail.xml'))
        self.check_submit_url_failed(response)

    def test_bad_url(self):
        self.login()
        response = self.submit_url('')
        self.check_submit_url_failed(response)
        response = self.submit_url(test_data_url('badfeed.html'))
        self.check_submit_url_failed(response)

    def test_submit_url_sets_defaults(self):
        self.login_and_submit_url()
        response = self.get_page('/channels/submit/step2')
        form = response.context[0]['form']
        def check_default(key, test_value):
            self.assertEquals(form.fields[key].initial, test_value)
        check_default('name', 'Rocketboom RSS 2.0 Main Index')
        check_default('website_url', 'http://www.rocketboom.com/vlog/')
        check_default('publisher', None)
        check_default('short_description', 'Daily with Joanne Colan')
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

    def check_submitted_languages(self, language, *secondary_languages):
        channel = self.get_last_channel()
        self.assertEquals(channel.language.id, language.id)
        channel_language_ids = [l.id for l in channel.secondary_languages]
        correct_ids = [l.id for l in secondary_languages]
        self.assertSameSet(channel_language_ids, correct_ids)

    def test_languages(self):
        self.login_and_submit_url()
        language1 = Language("french")
        language2 = Language("fooese")
        language3 = Language("barwegian")
        self.save_to_db(language1, language2, language3)
        response = self.submit(language=language1.id, language2=language2.id)
        self.check_submit_worked(response)
        self.check_submitted_languages(language1, language2)
        self.delete_last_channel()
        self.login_and_submit_url()
        response = self.submit(language=language3.id, language2=language2.id,
                language3=language3.id)
        self.check_submit_worked(response)
        self.check_submitted_languages(language3, language2)

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

    def test_submit_destroys_feed(self):
        self.login_and_submit_url()
        response = self.submit()
        self.check_submit_worked(response)
        response = self.get_page('/channels/submit/step2')
        self.assertEquals(response.status_code, 302)

    def test_submit_feed_then_go_back(self):
        self.login_and_submit_url()
        response = self.submit_url('')
        self.check_submit_url_failed(response)
        response = self.get_page('/channels/submit/step2')
        self.assertEquals(response.status_code, 302)

    def check_category_names(self, response, *correct_names):
        form = response.context[0]['form']
        names = [c[1] for c in form.fields['category1'].choices]
        self.assertSameSet(names, list(correct_names) + ['<none>'])

    def test_categories_widget_updates(self):
        self.login_and_submit_url()
        response = self.get_page('/channels/submit/step2')
        self.check_category_names(response, 'foo', 'bar')
        self.save_to_db(Category(name='baz'))
        response = self.get_page('/channels/submit/step2')
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
        response = self.submit(category1=self.cat1.id, category2=self.cat2.id, 
                category3=self.cat1.id)
        self.check_submit_worked(response)
        last = self.get_last_channel()
        category_ids = [c.id for c in last.categories]
        self.assertSameSet(category_ids, [self.cat1.id, self.cat2.id])

    def test_tag_limit(self):
        self.login_and_submit_url()
        response = self.submit(tags='a,b,c,d,e,f')
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
        self.login()
        response = self.submit_url(channel.url)
        form = response.context[0]['form']
        self.assertSameSet(form.errors.keys(), ['url'])

class ModerateChannelTest(ChannelTestBase):
    """Test the moderate channel web page."""

    def setUp(self):
        ChannelTestBase.setUp(self)
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
            self.save_to_db(self.channel)
            url = '/channels/%d' % self.channel.id
            self.post_data(url, {'action': 'change-state', 'submit': action})
            self.connection.commit()
            updated = self.refresh_record(self.channel)
            self.assertEquals(updated.state, state)
        check_state('Approve', Channel.APPROVED)
        check_state("Don't Know", Channel.DONT_KNOW)

    def test_approve_without_owner_email(self):
        self.channel.owner.email = None
        self.save_to_db(self.channel.owner)
        self.login('joe')
        url = '/channels/%d' % self.channel.id
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
            url = '/channels/%d' % self.channel.id
            self.post_data(url, {'action': 'standard-reject', 'submit': action})
            after = self.refresh_record(self.channel, 'notes')
            self.assertEquals(after.state, Channel.REJECTED)
            self.assertEquals(len(after.notes), len(before.notes) + 1)
            self.assertEquals(len(self.emails), starting_email_count + 1)
        check_rejection_button('Broken')
        check_rejection_button('Copyright')
        check_rejection_button('Explicit')
        check_rejection_button('No Video')

    def test_custom_reject(self):
        self.login('joe')
        title = 'CUSTOM TITLE'
        body = 'CUSTOM BODY'
        url = '/channels/%d' % self.channel.id
        self.post_data(url, {'action': 'reject', 'title': title, 'body':
            body})
        updated = self.refresh_record(self.channel, 'notes')
        self.assertEquals(updated.state, Channel.REJECTED)
        self.assertEquals(len(updated.notes), 1)
        self.assertEquals(len(self.emails), 1)

    def test_custom_reject_needs_title_and_body(self):
        self.login('joe')
        url = '/channels/%d' % self.channel.id
        self.post_data(url, {'action': 'reject', 'title': 'stuff', 'body':
            ''})
        updated = self.refresh_record(self.channel, 'notes')
        self.assertEquals(updated.state, Channel.NEW)
        self.post_data(url, {'action': 'reject', 'title': '', 'body':
            'stuff'})
        updated = self.refresh_record(self.channel, 'notes')
        self.assertEquals(updated.state, Channel.NEW)

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

    def channel_search(self, query):
        page = self.get_page('/search', data={'query': query})
        return page.context[0]['results']

    def search_items(self, query):
        page = self.get_page('/search', data={'query': query})
        return page.context[0]['item_results']

    def channel_search_count(self, query):
        page = self.get_page('/search', data={'query': query})
        return page.context[0]['results_count']

    def search_items_count(self, query):
        page = self.get_page('/search', data={'query': query})
        return page.context[0]['item_results_count']

    def check_search_redirects_to_channel(self, query, channel):
        page = self.get_page('/search', data={'query': query})
        self.assertRedirect(page, 'channels/%d' % channel.id)

    def test_channel_search(self):
        results = [c.id for c in self.channel_search("Rocketboom")]
        self.assertEquals(results, [self.channel.id])
        self.assertEquals(self.channel_search_count("Rocketboom"), 1)
        self.assertSameSet(self.channel_search("Sprocketboom"), [])
        self.assertEquals(self.channel_search_count("Sprocketboom"), 0)

    def test_item_search(self):
        results = [c.id for c in self.search_items("rb_06_dec_13")]
        self.assertEquals(results, [self.channel.id])
        self.assertEquals(self.search_items_count("rb_06_dec_13"), 1)
        self.assertSameSet(self.search_items("ze frank"), [])
        self.assertEquals(self.search_items_count("ze frank"), 0)

    def test_ordering(self):
        channel2 = self.make_channel(state=Channel.APPROVED)
        channel2.name = "Colan"
        channel2.save(self.connection)
        channel2.update_search_data(self.connection)
        self.connection.commit()
        # Having "Colan" in the title should trump "Colan" in the description
        results = self.channel_search("Colan")
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
        self.assertEquals(self.channel_search_count('Unapproved'), 0)

    def test_mods_see_unapproved(self):
        unapproved = self.make_unaprroved_channel()
        self.login(self.make_user('reggie', role=User.MODERATOR))
        self.check_search_redirects_to_channel('Unapproved', unapproved)

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
        self.channel.add_tag(self.connection, self.ralph, "funny")
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
        url = '/channels/edit/%d' % self.channel.id
        self.check_page_access(mod, url, True)
        self.check_page_access(self.ralph, url, True)
        self.check_page_access(other_user, url, False)

    def post_to_edit_page(self, data):
        url = '/channels/edit/%d' % self.channel.id
        return self.post_data(url, data)

    def test_change(self):
        self.login(self.ralph)
        data = {
                'url': self.channel.url,
                'category1': self.categories['arts'].id,
                'category3': self.categories['comedy'].id,
                'language': self.languages['klingon'].id,
                'language2': self.languages['piglatin'].id,
                'tags': 'funny, cool, booya',
                'publisher': 'some guy',
                'name': 'cool vids',
                'short_description': 'wow',
                'description': 'These are the best.',
                'website_url': 'http://www.google.com/',
        }

        self.post_to_edit_page(data)
        self.connection.commit()
        updated = self.refresh_record(self.channel, 'language', 'categories',
                'tags', 'secondary_languages')
        self.assertEquals(updated.publisher, 'some guy')
        self.assertEquals(updated.language.name, 'klingon')
        self.check_names(updated.categories, 'arts', 'comedy')
        self.check_names(updated.tags, 'funny', 'cool', 'booya')
        self.check_names(updated.secondary_languages, 'piglatin')

    def get_default_values(self):
        data = {}
        for key in ['publisher', 'name', 'short_description',
                'website_url', 'description', 'url']:
            data[key] = getattr(self.channel, key)
        for i in xrange(len(self.channel.categories)):
            data['category%d' % (i + 1)] = self.channel.categories[i].id
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
        data['short_description'] = '\xd8\x8d\xd8\xa8\xd8\xa8\xd8\xa6\xd8\xb5'
        data['description'] = '\xd8\x8d\xd8\xa8\xd8\xa8\xd8\xa6\xd8\xb5'
        self.post_to_edit_page(data)
        self.connection.commit()
        updated = self.refresh_record(self.channel, 'tags')

    def test_change_url(self):
        self.login(self.ralph)
        data = self.get_default_values()
        data['url'] = test_data_url('feed2.xml')
        url = '/channels/edit/%d' % self.channel.id
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

    def check_escaping(self):
        templates = [
            'channel-feature.html',
            'channel-feature-no-image.html',
            'channel-full.html',
            'channel-in-category.html',
            'channel-in-list.html',
            'channel-mini.html',
        ]
        context = {'channel': self.channel, 'BASE_URL': settings.BASE_URL}
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
        r = Rating()
        r.channel_id = self.channel.id
        r.user_id = new_user.id
        r.rating = 5
        self.save_to_db(r)
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
        r = Rating()
        r.channel_id = self.channel.id
        r.user_id = self.regular.id
        r.rating = 5
        self.save_to_db(r)
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
