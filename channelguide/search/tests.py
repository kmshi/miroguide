# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from channelguide.channels.models import Channel
from channelguide.search.models import ChannelSearchData
from channelguide.testframework import TestCase, test_data_path

class ChannelSearchTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.ralph = self.make_user('ralph')
        self.channel = self.make_channel()
        self.channel.update_items(
            feedparser_input=open(test_data_path('feed.xml')))
        self.channel.name = "Rocketboom"
        self.channel.description = ("Daily with Joanne Colan "
                "(that's right... Joanne Colan")
        self.channel.state = Channel.APPROVED
        self.channel.save()
        ChannelSearchData.objects.update(self.channel)
        # make bogus channels so that the the fulltext indexes work
        for x in range(10):
            c = self.make_channel(state=Channel.APPROVED)
            ChannelSearchData.objects.update(c)

    def make_channel(self, **kwargs):
        return TestCase.make_channel(self, self.ralph, **kwargs)

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
        channel2.save()
        ChannelSearchData.objects.update(channel2)
        # Having "Colan" in the title should trump "Colan" in the description
        results = self.feed_search("Colan")
        self.assertEquals(len(results), 2)
        self.assertEquals(results[0].name, channel2.name)
        self.assertEquals(results[1].name, self.channel.name)

    def make_unaprroved_channel(self):
        unapproved = self.make_channel()
        unapproved.name = "Unapproved"
        unapproved.save()
        ChannelSearchData.objects.update(unapproved)
        return unapproved

    def test_unapproved_hidden(self):
        self.make_unaprroved_channel()
        self.assertEquals(self.feed_search_count('Unapproved'), 0)

    def test_mods_see_unapproved(self):
        self.make_unaprroved_channel()
        self.login(self.make_user('reggie', group='cg_moderator'))
        self.assertEquals(self.feed_search_count('Unapproved'), 1)

    def test_short_word_search(self):
        self.channel.name = "foobar y barfoo"
        self.channel.save()
        ChannelSearchData.objects.update(self.channel)

        def _check(query):
            results = self.feed_search(query)
            self.assertEquals(len(results), 1)
            self.assertEquals(results[0].id, self.channel.id)

        _check("foobar barfoo")
        _check("foobar y barfoo")
