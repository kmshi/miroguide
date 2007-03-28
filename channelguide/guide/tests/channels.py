from datetime import datetime, timedelta
import os

from django.conf import settings
from sqlalchemy import desc

from channelguide.guide.models import Channel, Category, Tag, Item, User, Language
from channelguide.testframework import TestCase
from channelguide.util import read_file, random_string, hash_string

def test_data_path(filename):
    return os.path.join(os.path.dirname(__file__), 'data', filename)

def test_data_url(filename):
    return 'file://' + os.path.abspath(test_data_path(filename))

class ChannelTestBase(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.ralph = self.make_user('ralph')
        self.channel = self.make_channel()

    def make_channel(self):
        return TestCase.make_channel(self, self.ralph)

class ChannelTagTest(ChannelTestBase):
    """Test adding/removing/querying tags from channels."""

    def setUp(self):
        ChannelTestBase.setUp(self)
        self.ben = self.make_user('ben')
        self.nick = self.make_user('nick')

    def check_tags(self, *correct_tags):
        self.db_session.flush()
        self.db_session.refresh(self.channel)
        current_tags = [tag.name for tag in self.channel.tags]
        self.assertSameSet(current_tags, correct_tags)

    def test_tags(self):
        self.channel.add_tag(self.ben, 'funny')
        self.check_tags('funny')
        self.channel.add_tag(self.ben, 'cool')
        self.check_tags('funny', 'cool')
        self.channel.add_tags(self.nick, ['sexy', 'cool'])
        self.check_tags('funny', 'cool', 'sexy')
        self.channel.add_tag(self.nick, 'cool')
        self.check_tags('funny', 'cool', 'sexy')

    def test_duplicate_tags(self):
        self.channel.add_tag(self.ben, 'funny')
        self.channel.add_tag(self.nick, 'funny')
        count_select = self.db_session.query(Tag).select_by(name='funny')
        self.assertEquals(count_select.count(), 1)

    def check_tag_counts(self, name, user_count, channel_count):
        tag = self.query(Tag).get_by(name=name)
        self.db_session.refresh(tag)
        self.assertEquals(tag.user_count, user_count)
        self.assertEquals(tag.channel_count, channel_count)

    def test_info(self):
        self.channel.state = Channel.APPROVED
        self.db_session.save(self.channel)
        self.channel.add_tag(self.ben, 'funny')
        self.channel.add_tag(self.nick, 'funny')
        self.db_session.flush()
        self.check_tag_counts('funny', 2, 1)
        channel2 = self.make_channel()
        channel2.state = Channel.APPROVED
        channel2.add_tags(self.ben, ['tech', 'funny'])
        self.channel.add_tag(self.ben, 'tech')
        self.db_session.flush()
        self.check_tag_counts('funny', 2, 2)
        self.check_tag_counts('tech', 1, 2)
        non_active = self.make_channel()
        non_active.add_tag(self.nick, 'funny')
        non_active.add_tag(self.ben, 'funny')
        self.db_session.flush()
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
        image_data = read_file(test_data_path('thumbnail.jpg'))
        self.channel.save_thumbnail(image_data)
        self.check_thumb_exists('original')
        self.check_thumb_exists('60x40')
        self.check_thumb_exists('120x80')
        self.check_thumb_exists('252x169')
        self.assertEquals(image_data,
                read_file(self.get_thumb_path('original')))

    def test_approved_at(self):
        self.assertEquals(self.channel.approved_at, None)
        self.channel.change_state(Channel.APPROVED)
        timediff = datetime.now() - self.channel.approved_at
        self.assert_(timediff < timedelta(seconds=1))
        self.assert_(timediff > timedelta(seconds=0))
        self.channel.change_state(Channel.NEW)
        self.assertEquals(self.channel.approved_at, None)

    def test_thumbnail_before_save(self):
        c = Channel(url="http://myblog.com/videos/rss",
                website_url="http://myblog.com/", publisher="TestVision",
                short_description="stuff", description="lots of stuff")
        self.assertRaises(ValueError, c.save_thumbnail,
                read_file(test_data_path('thumbnail.jpg')))

    def test_subscription_counts(self):
        now = datetime.now()
        week = timedelta(days=7)
        def check_counts(total, month, today):
            self.db_session.refresh(self.channel)
            self.assertEquals(self.channel.subscription_count, total)
            self.assertEquals(self.channel.subscription_count_month, month)
            self.assertEquals(self.channel.subscription_count_today, today)

        check_counts(0, 0, 0)
        self.channel.add_subscription(self.connection)
        check_counts(1, 1, 1)
        self.channel.add_subscription(self.connection, timestamp=now-week*1)
        check_counts(2, 2, 1)
        self.channel.add_subscription(self.connection, timestamp=now-week*6)
        check_counts(3, 2, 1)

    def test_delete(self):
        ben = self.make_user('ben')
        self.channel.add_subscription(self.connection)
        self.channel.add_tag(ben, 'cool')
        self.db_session.flush()
        self.db_session.delete(self.channel)
        self.db_session.flush()

    def test_delete_user_with_tags(self):
        ben = self.make_user('ben')
        self.channel.add_tag(ben, 'cool')
        self.db_session.flush()
        self.db_session.delete(ben)
        self.db_session.flush()

class ChannelItemTest(ChannelTestBase):
    def check_item_titles(self, *correct_titles):
        self.assertEquals(len(self.channel.items), len(correct_titles))
        for i in range(len(correct_titles)):
            self.assertEquals(self.channel.items[i].name, correct_titles[i])

    def test_parse(self):
        self.channel.update_items(
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
        the enclousre URL is different and the GUID is different.
        """
        self.channel.update_items(
                feedparser_input=open(test_data_path('feed.xml')))
        self.db_session.flush()
        old_ids = [item.id for item in self.channel.items]
        self.channel.update_items(
                feedparser_input=open(test_data_path('feed-future.xml')))
        # 2 new channels, 2 channels are gone, the rest are the same
        # That the new feed has some entries where the GUID stays the same and
        # some where the enclosure URL stays the same
        # It also has 2 entries with the same enclosure URL to try to mess
        # with the CG logic
        self.db_session.flush()
        self.db_session.expire(self.channel)
        new_ids = [item.id for item in self.channel.items]
        self.assert_(new_ids[0] not in old_ids)
        self.assert_(new_ids[1] not in old_ids)
        self.assert_(old_ids[-1] not in new_ids)
        self.assert_(old_ids[-2] not in new_ids)
        self.assertEquals(new_ids[2:], old_ids[0:-2])

    def test_future_corner_cases(self):
        """Test some corder cases when we update a feed, duplicate URLS,
        duplicate GUIDs, items missing GUIDs and URLS.
        """
        self.channel.update_items(
                feedparser_input=open(test_data_path('feed-future.xml')))
        self.db_session.flush()
        self.channel.update_items(
                feedparser_input=open(test_data_path('feed-future-corner-cases.xml')))
        self.db_session.flush()
        self.db_session.refresh(self.channel)
        # Maybe we should test the behaviour here, but the main thing is the
        # guide shouldn't crash

    def test_thumbnails(self):
        width, height = Item.THUMBNAIL_SIZES[0]
        dir = '%dx%d' % (width, height)
        self.channel.update_items(
                feedparser_input=open(test_data_path('thumbnails.xml')))
        self.db_session.flush()
        self.channel.download_item_thumbnails()
        self.assertEquals(self.channel.items[0].thumbnail_url,
                "http://www.getdemocracy.com/images/"
                "x11-front-page-screenshots/02.jpg")
        thumb_path = os.path.join(settings.MEDIA_ROOT, Item.THUMBNAIL_DIR,
                dir, '%d.jpeg' % self.channel.items[0].id)
        cache_path = os.path.join(settings.IMAGE_DOWNLOAD_CACHE_DIR,
                hash_string(self.channel.items[0].thumbnail_url))
        self.assert_(os.path.exists(thumb_path))
        self.assert_(os.path.exists(cache_path))
        self.assert_(self.channel.items[0].thumbnail_exists())
        self.assert_(not self.channel.items[1].thumbnail_exists())
        self.assertEquals(self.channel.items[1].thumb_url(width, height),
                settings.IMAGES_URL + "missing.png")

    def test_item_info(self):
        self.db_session.refresh(self.channel)
        self.assertEquals(self.channel.item_count, 0)
        self.channel.update_items(
                feedparser_input=open(test_data_path('feed.xml')))
        self.db_session.flush()
        self.db_session.refresh(self.channel)
        self.assertEquals(self.channel.item_count, 5)

    def test_category_counts(self):
        def test(cat, test_count):
            self.db_session.refresh(cat)
            self.assertEquals(cat.channel_count, test_count)
        foo = Category(name='foo')
        bar = Category(name='bar')
        self.save_to_db(foo, bar)
        test(foo, 0)
        test(bar, 0)
        channel = self.make_channel()
        channel.state = Channel.APPROVED
        non_active = self.make_channel()
        channel.categories.append(foo)
        non_active.categories.append(bar)
        self.save_to_db(channel, non_active, foo, bar)
        self.db_session.refresh(foo)
        self.db_session.refresh(bar)
        test(foo, 1)
        test(bar, 0)

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
            'website_url': 'http://foo.com/' + random_string(16),
            'short_description': 'booya',
            'description': 'Awesome channel',
            'publisher': 'Foo incorporated',
            'language': self.language.id,
            'category1': self.cat1.id,
            'category2': self.cat2.id,
            'thumbnail': open(test_data_path('thumbnail.jpg')),
            'thumbnail_file_submitted_path': '',
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
        return self.db_session.query(Channel).select().list()[-1]

    def delete_last_channel(self):
        self.db_session.delete(self.get_last_channel())
        self.db_session.flush()

    def check_last_channel_thumbnail(self, thumb_name):
        last = self.get_last_channel()
        path = os.path.join(settings.MEDIA_ROOT, Channel.THUMBNAIL_DIR,
                'original', '%d.%s' % (last.id, last.thumbnail_extension))
        self.assert_(os.path.exists(path))
        right_data = read_file(test_data_path(thumb_name))
        actual_data = read_file(path)
        self.assert_(right_data == actual_data)

    def check_submit_url_failed(self, response):
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.template[0].name, 'guide/submit-feed-url.html')

    def check_submit_url_worked(self, response):
        self.assertEquals(response.status_code, 302)
        test_url = settings.BASE_URL + 'channels/submit/step2'
        self.assertEquals(response['Location'], test_url)

    def check_submit_failed(self, response):
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.template[0].name, 'guide/submit-channel.html')

    def check_submit_worked(self, response, thumb_name='thumbnail.jpg'):
        self.assertEquals(response.status_code, 302)
        test_url = settings.BASE_URL + 'channels/submit/after'
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
        self.db_session.refresh(channel)
        self.assertEquals(channel.language, language)
        self.assertSameSet(channel.secondary_languages, secondary_languages)

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
        self.refresh_connection()
        self.check_submit_worked(response)
        self.check_submitted_languages(language3, language2)

    def test_remembers_thumbnail(self):
        self.login_and_submit_url()
        response = self.submit(dont_send='name')
        self.check_submit_failed(response)
        response = self.submit(response, dont_send='thumbnail')
        self.check_submit_worked(response)

    def test_replace_thumbnail(self):
        self.login_and_submit_url()
        response = self.submit(dont_send='name')
        self.check_submit_failed(response)
        response = self.submit(response,
                thumbnail=open(test_data_path('thumbnail_square.png')))
        self.check_submit_worked(response, thumb_name='thumbnail_square.png')

    def test_replace_and_remember_thumbnail(self):
        self.login_and_submit_url()
        response = self.submit(dont_send='name')
        self.check_submit_failed(response)
        response = self.submit(response, dont_send='name',
                thumbnail=open(test_data_path('thumbnail_square.png')))
        response = self.submit(response, dont_send='thumbnail')
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
        self.assertSameSet(last.categories, [self.cat1, self.cat2])

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
        self.db_session.save(channel)
        self.db_session.flush()
        self.login()
        response = self.submit_url(channel.url)
        form = response.context[0]['form']
        self.assertSameSet(form.errors.keys(), ['url'])

class ModerateChannelTest(ChannelTestBase):
    """Test the moderate channel web page."""

    def setUp(self):
        ChannelTestBase.setUp(self)
        self.joe = self.make_user('joe')
        self.joe.role = User.MODERATOR
        self.db_session.update(self.joe)
        self.db_session.flush()
        self.schmoe = self.make_user('schmoe')

    def login(self, username):
        ChannelTestBase.login(self, username)
        return self.get_page('/channels/moderate')

    def test_moderator_required(self):
        response = self.get_page('/channels/moderate')
        self.assertEquals(response.status_code, 302)
        response = self.login('schmoe')
        self.assertEquals(response.status_code, 302)
        response = self.login('joe')
        self.assertEquals(response.status_code, 200)

    def do_moderate(self, channel, newstate):
        if newstate == Channel.APPROVED:
            action = 'Approve'
        elif newstate == Channel.REJECTED:
            action = 'Reject'
        elif newstate == Channel.WAITING:
            action = "Sent message"
        elif newstate == Channel.DONT_KNOW:
            action = "Don't Know"
        else:
            raise ValueError("Bad state: %s" % newstate)
        url = '/channels/%d' % channel.id
        return self.post_data(url, {'action': 'change-state', 'submit': action})

    def test_moderate_action(self):
        self.login('joe')
        def check_state(state):
            self.do_moderate(self.channel, state)
            self.refresh_connection()
            self.db_session.refresh(self.channel)
            self.assertEquals(self.channel.state, state)
        check_state(Channel.APPROVED)
        check_state(Channel.REJECTED)
        check_state(Channel.WAITING)
        check_state(Channel.DONT_KNOW)

class ChannelSearchTest(ChannelTestBase):
    def setUp(self):
        ChannelTestBase.setUp(self)
        self.channel.update_items(
                feedparser_input=open(test_data_path('feed.xml')))
        self.channel.name = "Rocketboom"
        self.channel.description = ("Daily with Joanne Colan "
                "(that's right... Joanne Colan")
        self.channel.update_search_data()
        # make bogus channels so that the the fulltext indexes work
        for x in range(10):
            c = self.make_channel()
            c.update_search_data()
        self.db_session.flush()

    def channel_search(self, query):
        return Channel.search(self.db_session, [query])

    def search_items(self, query):
        return Channel.search_items(self.db_session, [query])

    def channel_search_count(self, query):
        return Channel.search_count(self.connection, [query])

    def search_items_count(self, query):
        return Channel.search_items_count(self.connection, [query])

    def test_channel_search(self):
        self.assertSameSet(self.channel_search("Rocketboom"), [self.channel])
        self.assertEquals(self.channel_search_count("Rocketboom"), 1)
        self.assertSameSet(self.channel_search("Sprocketboom"), [])
        self.assertEquals(self.channel_search_count("Sprocketboom"), 0)

    def test_item_search(self):
        self.assertSameSet(self.search_items("rb_06_dec_13"), [self.channel])
        self.assertEquals(self.search_items_count("rb_06_dec_1"), 1)
        self.assertSameSet(self.search_items("ze frank"), [])
        self.assertEquals(self.search_items_count("ze frank"), 0)

    def test_ordering(self):
        channel2 = self.make_channel()
        channel2.name = "Colan"
        channel2.update_search_data()
        self.db_session.flush()
        # Having "Colan" in the title should trump "Colan" in the description
        results = self.channel_search("Colan")
        self.assertEquals(results[0].name, channel2.name)
        self.assertEquals(results[1].name, self.channel.name)
        self.assertEquals(len(results), 2)

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
        self.channel.categories.append(self.categories['arts'])
        self.channel.categories.append(self.categories['tech'])
        self.channel.add_tag(self.ralph, "funny")
        self.channel.add_tag(self.ralph, "awesome")
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

    def test_change(self):
        self.login(self.ralph)
        data = {
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
        url = '/channels/edit/%d' % self.channel.id
        self.post_data(url, data)
        self.refresh_db_object(self.channel)
        self.assertEquals(self.channel.publisher, 'some guy')
        self.assertEquals(self.channel.language.name, 'klingon')
        self.check_names(self.channel.categories, 'arts', 'comedy')
        self.check_names(self.channel.tags, 'funny', 'cool', 'booya')
        self.check_names(self.channel.secondary_languages, 'piglatin')

    def check_names(self, name_list, *correct_names):
        names = [i.name for i in name_list]
        self.assertSameSet(names, correct_names)
