import time

from django.core import mail
from django.conf import settings
from django.forms import fields

from channelguide.testframework import TestCase
from channelguide.cache import client
from channelguide import util

from channels import test_data_path

class SharingViewTestCase(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        owner = self.make_user('owner')
        self.channel = self.make_channel(owner)
        client.clear_cache()
        time.sleep(1)

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
        self.save_to_db(self.channel)
        self.refresh_connection()

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
        response = self.get_item(test_data_path('feed.xml'), 'file_url')

        channel = response.context[0]['channel']
        self.assertEquals(channel.fake, True)
        self.assertEquals(channel.name, 'Rocketboom RSS 2.0 Main Index')

        item = response.context[0]['item']
        self.assertEquals(item.fake, True)
        self.assertEquals(item.name, 'file_url')
        self.assertTrue(item.thumbnail_url is None)

    def test_item_url_in_database(self):
        self.channel.join('items').execute(self.connection)
        self.channel.url = test_data_path('feed.xml')
        self.save_to_db(self.channel)
        self.channel.update_items(self.connection,
                        feedparser_input=open(self.channel.url))
        self.refresh_connection()

        response = self.get_item(test_data_path('feed.xml'),
                                 'http://www.rocketboom.net/video/'
                                 'rb_06_dec_13.mov')
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response['Location'],
                          util.make_absolute_url(
                self.channel.items[0].get_url(), {'share': 'true'}))

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
        client.clear_cache()
        time.sleep(1)

    def tearDown(self):
        fields.URLField.clean = self.old_clean

    def test_email_required_fields(self):
        response = self.post_data('/share/email/', {})
        form = response.context['share_form']
        self.assertEquals(form.errors.keys(),
                          ['share_url', 'recipients', 'share_type', 'from_email'])

    def test_send_feed_email_not_in_database(self):
        data = {
            'feed_url': test_data_path('feed.xml'),
            'share_url': util.make_absolute_url('/share/feed/?feed_url=foo'),
            'share_type': 'feed',
            'from_email': 'test@test.com',
            'comment': 'this is my comment',
            'recipients': 'test2@test.com, test3@test.com'}
        response = self.post_data('/share/email/', data)
        self.assertFalse('share_form' in response.context)
        self.assertEquals(len(mail.outbox), 2)
        message = mail.outbox[0]
        self.assertEquals(message.from_email, settings.EMAIL_FROM)
        self.assertEquals(message.subject,
                          'test@test.com wants to share a video feed with you')
        self.assertTrue(data['comment'] in message.body)
        self.assertTrue(data['share_url'] in message.body)
        self.assertTrue('Rocketboom RSS 2.0 Main Index' in message.body)
        self.assertTrue('Daily with Joanne Colan' in message.body)

    def test_send_item_email_not_in_database(self):
        data = {
            'feed_url': test_data_path('feed.xml'),
            'file_url': 'http://www.rocketboom.net/video/rb_06_dec_13.mov',
            'share_url': util.make_absolute_url(
                '/share/item/?feed_url=foo&item_url=bar'),
            'share_type': 'item',
            'from_email': 'test@test.com',
            'comment': 'this is my comment',
            'recipients': 'test2@test.com, test3@test.com'}
        response = self.post_data('/share/email/', data)
        self.assertFalse('share_form' in response.context)
        self.assertEquals(len(mail.outbox), 2)
        message = mail.outbox[0]
        self.assertEquals(message.from_email, settings.EMAIL_FROM)
        self.assertEquals(message.subject,
                          'test@test.com wants to share a video with you')
        self.assertTrue(data['comment'] in message.body)
        self.assertTrue(data['share_url'] in message.body)
        self.assertTrue('rb_06_dec_13' in message.body)
        self.assertTrue('wii have a problem' in message.body)
