import time

from channelguide.testframework import TestCase
from channelguide.cache import client
from channelguide import util

from channels import test_data_path

class SharingViewTestCase(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.owner = self.make_user('owner')
        self.channel = self.make_channel(self.owner)
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

        item = response.context[0]['item']
        self.assertEquals(item.fake, True)
        self.assertEquals(item.name, 'rb_06_dec_13')

    def test_item_url_not_in_feed_or_database(self):
        response = self.get_item(test_data_path('feed.xml'), 'file_url')

        channel = response.context[0]['channel']
        self.assertEquals(channel.fake, True)
        self.assertEquals(channel.name, 'Rocketboom RSS 2.0 Main Index')

        item = response.context[0]['item']
        self.assertEquals(item.fake, True)
        self.assertEquals(item.name, 'file_url')


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
