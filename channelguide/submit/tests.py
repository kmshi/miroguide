import os

from django.conf import settings
from django.core.urlresolvers import reverse

from channelguide.testframework import TestCase, test_data_url, test_data_path
from channelguide.channels.models import Channel
from channelguide.labels.models import Category, Language
from channelguide import util

class SubmitChannelTest(TestCase):
    """Test the channel submit web pages."""

    def setUp(self):
        TestCase.setUp(self)
        self.joe = self.make_user('joe')
        self.cat1 = Category.objects.create(name='foo')
        self.cat2 = Category.objects.create(name='bar')

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
        return Channel.objects.order_by('-id')[0]

    def check_last_channel_thumbnail(self, thumb_name):
        last = self.get_last_channel()
        path = os.path.join(settings.MEDIA_ROOT, Channel.THUMBNAIL_DIR,
                'original', '%d.%s' % (last.id, last.thumbnail_extension))
        self.assert_(os.path.exists(path))
        right_data = file(test_data_path(thumb_name)).read()
        actual_data = file(path).read()
        self.assertEquals(right_data, actual_data, 'thumbnail does not match')

    def check_submit_url_failed(self, response):
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.template[0].name,
                          'submit/submit-feed-url.html')

    def check_submit_failed(self, response):
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.template[0].name,
                          'submit/submit-channel.html')

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
        self.assertEquals(response['Location'],
                          util.make_absolute_url('submit/after'))
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
        check_default('name', 'foo')
        check_default('website_url', 'http://www.rocketboom.com/vlog/')
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
        language2 = Language.objects.create(name="french")
        response = self.submit(language=self.language.id)
        self.check_submit_worked(response)
        self.check_submitted_language(self.language)
        self.get_last_channel().delete()
        self.login_and_submit_url()
        response = self.submit(language=language2.id)
        self.check_submit_worked(response)
        self.check_submitted_language(language2)

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
        self.submit(thumbnail_file=
                    open(test_data_path('thumbnail_square.png')))
        channel = self.get_last_channel()
        self.assertTrue(channel.thumbnail_exists())
        for size in channel.THUMBNAIL_SIZES:
            path = channel.thumb_path('%dx%d' % size)
            self.assertTrue(os.path.exists(path))
            self.assertEquals(os.path.splitext(path)[1], '.jpeg')
            self.assertEquals(util.get_image_extension(
                    file(path)), 'jpeg')


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
        Category.objects.create(name='baz')
        response = self.get_page('/submit/step2')
        self.check_category_names(response, 'foo', 'bar', 'baz')
        Category.objects.create(name='booya')
        response = self.submit(dont_send='name')
        self.check_category_names(response, 'foo', 'bar', 'baz', 'booya')

    def test_tags(self):
        self.login_and_submit_url()
        self.submit(tags=' foo, bar  , booya ')
        last = self.get_last_channel()
        current_tags = [tag.name for tag in last.tags.all()]
        self.assertSameSet(current_tags, ['foo', 'bar', 'booya'])

    def test_no_tags(self):
        self.login_and_submit_url()
        self.submit()
        last = self.get_last_channel()
        self.assertSameSet(last.tags.all(), [])

    def test_duplicate_category(self):
        self.login_and_submit_url()
        response = self.submit(categories_0=self.cat1.id,
                categories_1=self.cat2.id,
                categories_2=self.cat1.id)
        self.check_submit_worked(response)
        last = self.get_last_channel()
        self.assertSameSet(last.categories.all(), [self.cat1, self.cat2])

    def test_tag_limit(self):
        self.login_and_submit_url()
        response = self.submit(tags=','.join([str(i) for i in range(76)]))
        self.check_submit_failed(response)

    def test_empty_tag(self):
        def check_tags(tags, correct_tags):
            response = self.login_and_submit_url()
            response = self.submit(tags=tags)
            self.check_submit_worked(response)
            last = self.get_last_channel()
            self.assertEquals(last.tags.count(), len(correct_tags))
            for i in range(len(correct_tags)):
                self.assertEquals(last.tags.all()[i].name, correct_tags[i])
        check_tags('a,  ,b', ['a', 'b'])
        self.get_last_channel().delete()
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
        channel.save()
        mod = self.make_user('moderator', group='cg_moderator')
        TestCase.login(self, mod)
        response = self.post_data('/submit/step1', {'name': 'New Site'})
        self.assertRedirect(response, '/submit/step2')

        response = self.submit(dont_send='url',
                               website_url=channel.website_url)
        self.assertEquals(response.context[0]['form'].errors.keys(),
                          ['website_url'])
        # should work if the other channel is a feed
        channel.url = 'http://www.myblog.com/'
        channel.save()
        response = self.submit(dont_send='url',
                               website_url=channel.website_url)
        self.check_submit_worked(response)

    def test_claim_adds_note_to_channel(self):
        ralph = self.make_user('ralph')
        channel = self.make_channel(ralph)
        self.login_and_submit_url()
        self.submit_url(channel.url)

        claim_url = reverse('channelguide.submit.views.claim')
        self.post_data(claim_url, {})

        channel = Channel.objects.get(pk=channel.pk)
        self.assertFalse(channel.waiting_for_reply_date is None)
        self.assertEquals(channel.notes.all()[0].user, self.joe)
