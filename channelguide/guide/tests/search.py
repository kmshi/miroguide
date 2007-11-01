from channelguide.guide.views import search
from channelguide import manage
from channelguide.testframework import TestCase

class SearchTestCase(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.owner = self.make_user('wally', role='A')
        self.normal = self.make_channel(self.owner, state='A')
        self.not_approved = self.make_channel(self.owner)
        self.unicode = self.make_channel(self.owner, state='A')
        self.unicode.name = u'\u6771\u68ee\u65b0\u805e'
        self.unicode.save(self.connection)
        self.refresh_connection()
        manage.update_search_data()
        self.refresh_connection()

    def check_same_channels(self, list1, list2):
        self.assertEquals([c.id for c in list1], [c.id for c in list2])

    def test_search_channels(self):
        request = self.process_request()
        rows = search.search_channels(request, 'Channel').execute(self.connection)
        self.check_same_channels(rows, [self.normal])

    def test_search_channels_as_moderator(self):
        """
        Search for channels as a moderator should include all channels, not
        just approved ones.
        """
        request = self.process_request()
        request.user = self.owner
        rows = search.search_channels(request, 'Channel').execute(self.connection)
        self.check_same_channels(rows, [self.normal, self.not_approved])

    def test_search_for_unicode(self):
        request = self.process_request()
        rows = search.search_channels(request, u'\u6771\u68ee\u65b0').execute(self.connection)
        self.check_same_channels(rows, [self.unicode])
