from channelguide.guide.views import search
from channelguide.guide.models import Item, Language
from channelguide import manage
from channelguide.testframework import TestCase

class SearchTestCase(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.owner = self.make_user('wally', role='A')
        self.normal = self.make_channel(self.owner, state='A')
        self.make_item(self.normal, 'Item')
        self.not_approved = self.make_channel(self.owner)
        self.make_item(self.not_approved, 'Item')
        self.unicode = self.make_channel(self.owner, state='A')
        self.unicode.name = u'\u6771\u68ee\u65b0\u805e'
        self.unicode_lang = Language(u'\u015febnem')
        self.save_to_db(self.unicode_lang)
        self.unicode.primary_language_id = self.unicode_lang.id
        self.save_to_db(self.unicode)
        self.make_item(self.unicode, u'\u5f20\u9753\u9896\u5f20')
        self.refresh_connection()
        manage.update_search_data()
        self.refresh_connection()

    def make_item(self, channel, name):
        item = Item()
        item.channel_id = channel.id
        item.url = channel.url
        item.description = channel.description
        item.name = name
        item.save(self.connection)
        return item

    def check_same_records(self, list1, list2):
        self.assertEquals([c.id for c in list1], [c.id for c in list2])

    def test_search_channels(self):
        request = self.process_request()
        rows = search.search_channels(request, 'Channel').execute(self.connection)
        self.check_same_records(rows, [self.normal])

    def test_search_channels_as_moderator(self):
        """
        Search for channels as a moderator should include all channels, not
        just approved ones.
        """
        request = self.process_request()
        request.user = self.owner
        rows = search.search_channels(request, 'Channel').execute(self.connection)
        self.check_same_records(rows, [self.normal, self.not_approved])

    def test_search_channel_for_unicode(self):
        request = self.process_request()
        rows = search.search_channels(request, u'\u6771\u68ee\u65b0').execute(self.connection)
        self.check_same_records(rows, [self.unicode])

    def test_search_items(self):
        request = self.process_request()
        rows = search.search_items(request, 'Item').execute(self.connection)
        self.check_same_records(rows, [self.normal])

    def test_search_items_as_moderator(self):
        """
        Search for items as a moderator should include all channels, not
        just approved ones.
        """
        request = self.process_request()
        request.user = self.owner
        rows = search.search_items(request, 'Item').execute(self.connection)
        self.check_same_records(rows, [self.normal, self.not_approved])

    def test_search_item_for_unicode(self):
        request = self.process_request()
        rows = search.search_items(request, u'\u5f20\u9753\u9896\u5f20').execute(self.connection)
        self.check_same_records(rows, [self.unicode])

    def test_search_results(self):
        rows = search.search_results(self.connection, Language,
                ['booy'])
        self.check_same_records(rows, [self.normal])

    def test_search_results_unicode(self):
        rows = search.search_results(self.connection, Language,
                [u'\u015feb'])
        self.check_same_records(rows, [self.unicode_lang])
