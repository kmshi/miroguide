from django.core import mail
from django.conf import settings
from django.forms import fields

from channelguide.testframework import TestCase, test_data_path
from channelguide import util

class SharingViewTestCase(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        owner = self.make_user('owner')
        self.channel = self.make_channel(owner)

    def get_feed(self, feed_url):
        return self.get_page('/share/feed/', data={'feed_url': feed_url})

    def get_item(self, feed_url, file_url):
        return self.get_page('/share/item/', data={'feed_url': feed_url,
                                                   'file_url': file_url})

    def test_feed_url_not_in_database(self):
        response = self.get_feed(test_data_path('feed.xml'))
        channel = response.context[0]['channel']
        self.assertEquals(channel.fake, True)
        self.assertEquals(channel.name, 'Rocketboom RSS 2.0 Main Index')
        self.assertFalse(channel.thumbnail_url is None)

        item_page = response.context[0]['item_page']
        self.assertEquals(len(item_page.object_list), 5)

    def test_feed_url_in_database(self):
        self.channel.url = test_data_path('feed.xml')
        self.channel.save()

        response = self.get_feed(self.channel.url)
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response['Location'],
                            self.channel.get_absolute_url() + '?share=true')

    def test_item_url_in_feed_not_in_database(self):
        response = self.get_item(test_data_path('feed.xml'),
                                 'http://www.rocketboom.net/video/'
                                 'rb_06_dec_13.mov')

        channel = response.context[0]['channel']
        self.assertEquals(channel.fake, True)
        self.assertEquals(channel.name, 'Rocketboom RSS 2.0 Main Index')
        self.assertFalse(channel.thumbnail_url is None)

        item = response.context[0]['item']
        self.assertEquals(item.fake, True)
        self.assertEquals(item.name, 'rb_06_dec_13')
        self.assertFalse(item.thumbnail_url is None)

    def test_item_url_not_in_feed_or_database(self):
        response = self.get_item(test_data_path('feed.xml'),
                                 'http://google.com/')

        channel = response.context[0]['channel']
        self.assertEquals(channel.fake, True)
        self.assertEquals(channel.name, 'Rocketboom RSS 2.0 Main Index')

        item = response.context[0]['item']
        self.assertEquals(item.fake, True)
        self.assertEquals(item.name, 'http://google.com/')
        self.assertTrue(item.thumbnail_url is None)

    def test_item_url_in_database(self):
        self.channel.url = test_data_path('feed.xml')
        self.channel.save()
        self.channel.update_items(
            feedparser_input=open(self.channel.url))

        response = self.get_item(test_data_path('feed.xml'),
                                 'http://www.rocketboom.net/video/'
                                 'rb_06_dec_13.mov')
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response['Location'],
                          util.make_absolute_url(
                self.channel.items.all()[0].get_url(), {'share': 'true'}))

class SharingEmailTestCase(TestCase):

    def _patch_urlfield_clean(self, value):
        if not value:
            return u''
        return value

    def setUp(self):
        TestCase.setUp(self)
        self.old_clean = fields.URLField.clean
        fields.URLField.clean = self._patch_urlfield_clean
        owner = self.make_user('owner')
        self.channel = self.make_channel(owner)

    def tearDown(self):
        fields.URLField.clean = self.old_clean

    def test_email_required_fields(self):
        response = self.post_data('/share/email/', {})
        form = response.context['share_form']
        self.assertEquals(form.errors.keys(),
                          ['share_url', 'recipients', 'share_type',
                           'from_email'])

    def _feed_data(self):
        return {
            'feed_url': test_data_path('feed.xml'),
            'share_url': util.make_absolute_url('/share/feed/?feed_url=foo'),
            'share_type': 'feed',
            'from_email': 'test@test.com',
            'comment': 'this is my comment',
            'recipients': 'test2@test.com, test3@test.com'}

    def _item_data(self):
        return {
            'feed_url': test_data_path('feed.xml'),
            'file_url': 'http://www.rocketboom.net/video/rb_06_dec_13.mov',
            'share_url': util.make_absolute_url(
                '/share/item/?feed_url=foo&item_url=bar'),
            'share_type': 'item',
            'from_email': 'test@test.com',
            'comment': 'this is my comment',
            'recipients': 'test2@test.com, test3@test.com'}

    def _basic_mail_tests(self, data):
        self.assertEquals(len(mail.outbox), 2)
        message = mail.outbox[0]
        self.assertEquals(message.from_email, settings.EMAIL_FROM)
        self.assertTrue(data['comment'] in message.body)
        self.assertTrue(data['share_url'] in message.body)
        return message

    def test_send_feed_email_not_in_database(self):
        data = self._feed_data()
        self.post_data('/share/email/', data)
        message = self._basic_mail_tests(data)
        self.assertEquals(message.subject,
                          'test@test.com wants to share a video feed with you')
        self.assertTrue('Rocketboom RSS 2.0 Main Index' in message.body)
        self.assertTrue('Daily with Joanne Colan' in message.body)

    def test_send_item_email_in_feed_not_in_database(self):
        data = self._item_data()
        self.post_data('/share/email/', data)
        message = self._basic_mail_tests(data)
        self.assertEquals(message.subject,
                          'test@test.com wants to share a video with you')
        self.assertTrue('rb_06_dec_13' in message.body)
        self.assertTrue('wii have a problem' in message.body)

    def test_send_item_email_not_in_feed_or_database(self):
        data = self._item_data()
        data['file_url'] = 'http://google.com/foo_bar'
        self.post_data('/share/email/', data)
        message = self._basic_mail_tests(data)
        self.assertEquals(message.subject,
                          'test@test.com wants to share a video with you')
        self.assertFalse(data['file_url'] in message.body)
        self.assertTrue('foo_bar' in message.body)

    def test_send_feed_email_in_database(self):
        self.channel.url = test_data_path('feed.xml')
        self.channel.save()

        data = self._feed_data()
        self.post_data('/share/email/', data)
        message = self._basic_mail_tests(data)
        self.assertEquals(message.subject,
                          'test@test.com wants to share a video feed with you')
        self.assertTrue(self.channel.name in message.body)
        self.assertTrue(self.channel.description in message.body)


    def test_send_item_email_in_database(self):
        self.channel.url = test_data_path('feed.xml')
        self.channel.save()
        self.channel.update_items(
            feedparser_input=open(self.channel.url))

        data = self._item_data()
        self.post_data('/share/email/', data)
        message = self._basic_mail_tests(data)
        self.assertEquals(message.subject,
                          'test@test.com wants to share a video with you')
        self.assertTrue('rb_06_dec_13' in message.body)
        self.assertTrue('wii have a problem' in message.body)

    def test_description_capped_at_170_characters(self):
        self.channel.url = test_data_path('feed.xml')
        self.channel.description = 'a' * 200
        self.channel.save()

        data = self._feed_data()
        self.post_data('/share/email/', data)
        message = self._basic_mail_tests(data)
        self.assertFalse(self.channel.description in message.body)
        self.assertTrue(('a' * 167 + '...') in message.body)
