# Copyright (c) 2009 Participatory Culture Foundation
# See LICENSE for details.

from datetime import datetime, timedelta
import simplejson

from django.conf import settings
from django.core.management import call_command
from django.utils.importlib import import_module

from channelguide.channels.models import Item
from channelguide.labels.models import Category, Language
from channelguide.ratings.models import Rating
from channelguide.search.models import ChannelSearchData
from channelguide.subscriptions.models import Subscription
from channelguide.testframework import TestCase, test_data_path
from channelguide.api import utils

class ChannelApiTestBase(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.owner = self.make_user('owner')
        self.owner.get_profile().approved = True
        self.owner.get_profile().save()
        self.channels = []
        for i in range(2):
            channel = self.make_channel(self.owner, state='A')
            channel.name = 'My Channel %i' % i
            channel.save()
            self.channels.append(channel)
        self.categories = categories = []
        self.languages = languages = []
        items = []
        for n in range(2):
            cat = Category(name='category%i' % n)
            cat.save()

            lang = Language(name='language%i' % n)
            lang.save()

            item = Item()
            item.channel_id = self.channels[0].id
            item.url = self.channels[0].url
            item.name = 'item%i' % n
            item.description = 'Item'
            item.size = i
            item.date = datetime.now()
            item.save()
            item.save_thumbnail(
                    file(test_data_path('thumbnail.jpg')))

            categories.append(cat)
            languages.append(lang)
            items.append(item)
        self.channels[0].categories.add(*categories)
        self.channels[0].language = languages[0]
        self.channels[0].add_tags(self.owner,
                                  ['tag0', 'tag1'])
        self.channels[0].save_thumbnail(
                file(test_data_path('thumbnail.jpg')))

        self.channels[1].description = 'This is a different description.'
        self.channels[1].save()

        # the order is important because of throttling so we do them in reverse
        # order
        Subscription.objects.add(self.channels[0], '123.123.123.123',
                                 timestamp=datetime.now() - timedelta(days=1))
        Subscription.objects.add(self.channels[0], '123.123.123.123')
        for i in range(5):
            user = self.make_user('foo%i' % i)
            user.get_profile().approved = True
            user.get_profile().save()
            for channel in self.channels:
                rating, _ = Rating.objects.get_or_create(channel=channel,
                                                         user=user)
                rating.rating = i + 1
                rating.save()



class ChannelApiViewTest(ChannelApiTestBase):

    def make_api_request(self, request, **kw):
        url = '/api/' + request
        return self.get_page(url, data=kw)

    def test_python_response(self):
        """
        Making a request with no datatype should return a Python object.
        """
        response = self.get_page('/api/test')
        self.assertEquals(response.status_code, 200, response.content)
        self.assertEquals(eval(response.content),
                {'text': 'Valid request'})

    def test_json_response(self):
        """
        Making a request with datatype=json should return a JSON object instead
        of a Python object.
        """
        response = self.get_page('/api/test', data={'datatype': 'json'})
        self.assertEquals(simplejson.loads(response.content),
                          {'text': 'Valid request'})

    def test_json_callback(self):
        """
        A request with datatype=json and jsoncallback=<function name> should
        return a string which calls the given function with the data.
        """
        response = self.get_page('/api/test', data = {'datatype': 'json',
                                                    'jsoncallback': 'foo'})

        self.assertEquals(response['Content-Type'], 'text/javascript')

        content = response.content
        self.assertTrue(content.startswith('foo('),
                        'content does not start with function call: %r'%
                        content)
        self.assertTrue(content.endswith(');'))
        self.assertEquals(simplejson.loads(response.content[4:-2]),
                          {'text': 'Valid request'})

    def _verifyChannelResponse(self, response, channel):
        self.assertEquals(response.status_code, 200)

        data = eval(response.content)
        self.assertEquals(data['id'], channel.id)
        self.assertEquals(data['name'], channel.name)
        self.assertEquals(data['description'], channel.description)
        self.assertEquals(data['url'], channel.url)
        self.assertEquals(data['website_url'], channel.website_url)
        self.assertEquals(data['language'], 'language0')
        self.assertEquals(data['category'], ('category0', 'category1'))
        self.assertEquals(data['tag'], ('tag0', 'tag1'))
        self.assert_('thumbnail_url' in data)
        self.assertEquals(len(data['item']), 2)
        for i in range(2):
            item = data['item'][i]
            self.assertEquals(item['name'], 'item%i' % (1-i))
            self.assertEquals(item['description'], 'Item')
            self.assertEquals(item['url'], channel.url)
            self.assert_(item.get('size') is not None)
            self.assert_(item.get('date') is not None)
            self.assert_('thumbnail_url' in item)

    def test_get_channel(self):
        """
        /api/get_channel should return the information for a channel given
        its id.
        """
        # add a rating
        rating, created = Rating.objects.get_or_create(
            channel=self.channels[0], user=self.owner)
        rating.rating = 3
        rating.save()

        # put the subscription into the stats table
        call_command('refresh_stats_table')

        channel = self.channels[0]
        response = self.make_api_request('get_channel', id=channel.id)
        self._verifyChannelResponse(response, channel)

        data = eval(response.content)
        self.assertEquals(data['average_rating'], 3)
        self.assertEquals(data['subscription_count_today'], 1)
        self.assertEquals(data['subscription_count_month'], 2)
        self.assertEquals(data['subscription_count'], 2)

    def test_get_channel_404(self):
        """
        /api/get_channel with a channel id that doesn't exist should return a
        404.
        """
        response = self.make_api_request('get_channel', id=-1)
        self.assertEquals(response.status_code, 404)
        self.assertEquals(eval(response.content),
                {'error': 'CHANNEL_NOT_FOUND',
                 'text': 'Channel -1 not found'})

        response = self.make_api_request('get_channel', id='all')
        self.assertEquals(response.status_code, 404)
        self.assertEquals(eval(response.content),
                {'error': 'CHANNEL_NOT_FOUND',
                 'text': 'Channel all not found'})


    def test_get_channel_multiple_ids(self):
        """
        /api/get_channel should take multiple ids and return a list of the
        channels.
        """
        response = self.make_api_request('get_channel', id=(
                self.channels[0].id,
                self.channels[1].id))
        self.assertEquals(response.status_code, 200)
        data = eval(response.content)
        self.assertEquals(type(data), list)
        self.assertEquals(data[0]['id'], self.channels[0].id)
        self.assertEquals(data[1]['id'], self.channels[1].id)

    def test_get_channel_url(self):
        """
        A get_channel request with a URL should function just like a request
        with a channel ID.
        """
        channel = self.channels[0]
        response = self.make_api_request('get_channel', url=channel.url)
        self._verifyChannelResponse(response, channel)

        response = self.make_api_request('get_channel', url=channel.url[:-5])
        self.assertEquals(response.status_code, 404)
        self.assertEquals(eval(response.content),
                {'error': 'CHANNEL_NOT_FOUND',
                 'text': 'Channel %s not found' % channel.url[:-5]})

    def test_get_channel_combine_url_id(self):
        """
        /api/get_channel should handle mixing url and id lookups.
        """
        response = self.get_page('/api/get_channel', data=
                                 [('url', self.channels[0].url),
                                  ('id', self.channels[01].id)])
        self.assertEquals(response.status_code, 200)
        data = eval(response.content)
        self.assertEquals(len(data), 2)
        self.assertEquals(data[0]['url'], self.channels[1].url)
        self.assertEquals(data[1]['id'], self.channels[0].id)

    def test_get_channels(self):
        response = self.make_api_request('get_channels', filter='category',
            filter_value='category0')
        self.assertEquals(response.status_code, 200)
        data = eval(response.content)
        self.assert_(isinstance(data, list))
        self.assertEquals(data[0]['id'], self.channels[0].id)

    def test_get_feeds_sites(self):
        self.channels[1].url = None
        self.channels[1].save ()

        response = self.make_api_request('get_feeds', filter='name',
            filter_value='My')
        self.assertEquals(response.status_code, 200)
        data = eval(response.content)
        self.assert_(isinstance(data, list))
        self.assertEquals(len(data), 1)
        self.assertEquals(data[0]['id'], self.channels[0].id)

        response = self.make_api_request('get_sites', filter='name',
            filter_value='My')
        self.assertEquals(response.status_code, 200)
        data = eval(response.content)
        self.assert_(isinstance(data, list))
        self.assertEquals(len(data), 1)
        self.assertEquals(data[0]['id'], self.channels[1].id)

    def test_get_session(self):
        response = self.make_api_request('get_session')
        self.assertEquals(response.status_code, 200)
        data = eval(response.content)
        self.assertEquals(len(data['session']), 32)

    def _do_authentication(self,  response):
        self.assertEquals(response.status_code, 200)
        context = response.context[0]

        data = {'verification': context['verification']
              }
        if context.get('session'):
            data['session'] = context['session']
        if context.get('redirect'):
            data['redirect'] = context['redirect']

        return self.post_data('/api/authenticate', data, self.owner)

    def _get_session(self):
        response = self.get_page('/api/authenticate', self.owner)
        response = self._do_authentication(response)
        return response.context[0]['session']

    def test_authenticate(self):
        response = self.get_page('/api/authenticate', self.owner, {
                'redirect': 'http://test.com/'})
        context = response.context[0]
        self.assertEquals(context['session'], None)
        self.assertEquals(context['redirect'], 'http://test.com/')
        response = self._do_authentication(response)
        self.assertRedirect(response, 'http://test.com/')
        self.assert_('?session=' in response['Location'])
        engine = import_module(settings.SESSION_ENGINE)
        session = engine.SessionStore(
            response['Location'][-32:])
        self.assertEquals(session['apiUser'], self.owner.id)


    def test_authenticate_without_redirect(self):
        response = self.get_page('/api/authenticate', self.owner)
        response = self._do_authentication(response)
        self.assertEquals(response.context[0]['success'], True)

    def test_authenticate_with_session(self):
        engine = import_module(settings.SESSION_ENGINE)
        sessionID = engine.SessionStore(None).session_key
        response = self.get_page('/api/authenticate', self.owner,
                                 {'redirect': 'http://test.com/',
                                  'session': sessionID})
        response = self._do_authentication(response)
        self.assertRedirect(response, 'http://test.com/')
        self.assertEquals(response['Location'], 'http://test.com/?session=%s'
                            % sessionID)

    def test_authenticate_not_verified(self):
        response = self.post_data('/api/authenticate', {'verification': 'foo'},
                                  self.owner)
        self.assertNotEquals(response.context[0].get('error'), None)

    def test_rate(self):
        session = self._get_session()
        response = self.make_api_request('rate', id=-1,
                                         session=session)
        self.assertEquals(response.status_code, 404)
        self.assertEquals(eval(response.content),
                          {'error': 'CHANNEL_NOT_FOUND',
                           'text': 'Channel -1 not found'})
        response = self.make_api_request('rate', id=self.channels[0].id,
                                         session='invalid session')
        self.assertEquals(response.status_code, 403)
        self.assertEquals(eval(response.content),
                          {'error': 'INVALID_SESSION',
                           'text': 'Invalid session'})

        response = self.make_api_request('rate', id=self.channels[0].id,
                                         session=session)
        self.assertEquals(response.status_code, 200)
        data = eval(response.content)
        self.assertEquals(data, {'rating': None})

        response = self.make_api_request('rate', id=self.channels[0].id,
                                         session=session,
                                         rating=5)
        self.assertEquals(response.status_code, 200)
        data = eval(response.content)
        self.assertEquals(data, {'rating': 5})

        response = self.make_api_request('rate', id=self.channels[0].id,
                                         session=session)
        self.assertEquals(response.status_code, 200)
        data = eval(response.content)
        self.assertEquals(data, {'rating': 5})

    def test_get_ratings(self):
        session = self._get_session()
        rating, created = Rating.objects.get_or_create(
            channel=self.channels[0], user=self.owner)
        rating.rating = 5
        rating.save()
        rating, created = Rating.objects.get_or_create(
            channel=self.channels[1], user=self.owner)
        rating.rating = 4
        rating.save()

        response = self.make_api_request('get_ratings',
                                         session=session)
        self.assertEquals(response.status_code, 200)
        data = eval(response.content)
        self.assertEquals(len(data), 2)
        for channel in data:
            if channel['id'] == self.channels[0].id:
                self.assertEquals(channel['rating'], 5)
            elif channel['id'] == self.channels[1].id:
                self.assertEquals(channel['rating'], 4)
            else:
                self.fail('unknown channel id: %i' % channel['id'])

    def test_get_ratings_filter(self):
        session = self._get_session()
        rating, created = Rating.objects.get_or_create(
            channel=self.channels[0], user=self.owner)
        rating.rating = 5
        rating.save()
        rating, created = Rating.objects.get_or_create(
            channel=self.channels[1], user=self.owner)
        rating.rating = 4
        rating.save()

        response = self.make_api_request('get_ratings',
                                         session=session,
                                         rating='4')
        self.assertEquals(response.status_code, 200)
        data = eval(response.content)
        self.assertEquals(len(data), 1)
        self.assertEquals(data[0]['id'], self.channels[1].id)

    def test_get_recommendations(self):
        session = self._get_session()
        response = self.make_api_request('get_recommendations',
                                         session='invalid session')
        self.assertEquals(response.status_code, 403)
        self.assertEquals(eval(response.content),
                          {'error': 'INVALID_SESSION',
                           'text': 'Invalid session'})
        self.owner.approved = True
        self.owner.save()
        rating, created = Rating.objects.get_or_create(
            channel=self.channels[0], user=self.owner)
        rating.rating = 5
        rating.save()

        call_command('refresh_stats_table')
        call_command('calculate_recommendations')
        response = self.make_api_request('get_recommendations',
                                         session=session)
        self.assertEquals(response.status_code, 200)
        data = eval(response.content)
        self.assertEquals(len(data), 1)
        self.assertEquals(data[0]['id'], self.channels[1].id)
        self.assertEquals(data[0]['guessed'], 5.0)
        self.assertEquals(len(data[0]['reasons']), 1)
        self.assertEquals(data[0]['reasons'][0]['id'], self.channels[0].id)
        self.assertTrue(data[0]['reasons'][0]['score'] > 0.5)

    def test_list_categories(self):
        response = self.make_api_request('list_categories')
        self.assertEquals(response.status_code, 200)
        data = eval(response.content)
        self.assertEquals(len(data), 2)
        for i in range(2):
            self.assertEquals(data[i]['name'], self.categories[i].name)
            self.assertEquals(data[i]['url'],
                              self.categories[i].get_absolute_url())

    def test_list_languages(self):
        response = self.make_api_request('list_languages')
        self.assertEquals(response.status_code, 200)
        data = eval(response.content)
        self.assertEquals(len(data), 3)
        languages = [self.language] + self.languages
        for i in range(3):
            self.assertEquals(data[i]['name'], languages[i].name)
            self.assertEquals(data[i]['url'],
                              languages[i].get_absolute_url())


class MockRequest(object):

    def __init__(self, test):
        self.user = test.owner
        self.session = {}

class ChannelApiFunctionTest(ChannelApiTestBase):

    def make_request(self):
        return MockRequest(self)

    def assertSameChannels(self, l1, l2):
        self.assertEquals([c.id for c in l1], [c.id for c in l2])

    def test_get_channel(self):
        """
        utils.get_channel(conection, id) should return a full channel object,
        with categories, tags, and items.
        """
        # add a rating
        rating, created = Rating.objects.get_or_create(
            channel=self.channels[0], user=self.owner)
        rating.rating = 3
        rating.save()

        call_command('refresh_stats_table')

        obj = utils.get_channel(self.channels[0].id)
        self.assertEquals(obj.id, self.channels[0].id)
        self.assertEquals(obj.url, self.channels[0].url)
        self.assertEquals(obj.owner.username, 'owner')
        self.assertEquals(len(obj.categories.all()), 2)
        self.assertEquals(len(obj.tags.all()), 2)
        self.assertEquals(len(obj.items.all()), 2)
        self.assertEquals(obj.stats.subscription_count_today, 1)
        self.assertEquals(obj.stats.subscription_count_month, 2)
        self.assertEquals(obj.stats.subscription_count, 2)
        self.assertEquals(obj.rating.average, 3)


    def test_get_channel_by_url(self):
        """
        utils.get_channel_by_url(url0 should return a full channel
        object with categories, tags, and items.
        """
        obj = utils.get_channel_by_url(self.channels[0].url)
        self.assertEquals(obj.id, self.channels[0].id)
        self.assertEquals(obj.url, self.channels[0].url)
        self.assertEquals(obj.owner.username, 'owner')
        self.assertEquals(len(obj.categories.all()), 2)
        self.assertEquals(len(obj.tags.all()), 2)
        self.assertEquals(len(obj.items.all()), 2)

    def test_get_channels_filter_category(self):
        """
        utils.get_channels('category', 'category name') should
        return a list of Channels that belong to that category.
        """
        objs = utils.get_channels(self.make_request(), 'category', 'category0')
        self.assertEquals(len(objs), 1)
        self.assertEquals(objs[0].id, self.channels[0].id)

        objs2 = utils.get_channels(self.make_request(), 'category', 'unknown')
        self.assertEquals(len(objs2), 0)

    def test_get_channels_filter_tag(self):
        """
        utils.get_channels('tag', 'tag name') should
        return a list of Channels that belong to that category.
        """
        objs = utils.get_channels(self.make_request(), 'tag', 'tag0')
        self.assertEquals(len(objs), 1)
        self.assertEquals(objs[0].id, self.channels[0].id)

        objs2 = utils.get_channels(self.make_request(), 'tag', 'unknown')
        self.assertEquals(len(objs2), 0)

    def test_get_channels_filter_language(self):
        """
        utils.get_channels('language', 'language name') should
        return a list of Channels that belong to that category.
        """
        objs = utils.get_channels(self.make_request(), 'language', 'language0')
        self.assertEquals(len(objs), 1)
        self.assertEquals(objs[0].id, self.channels[0].id)

        objs3 = utils.get_channels(self.make_request(), 'language', 'unknown')
        self.assertEquals(len(objs3), 0)

    def test_get_channels_filter_featured(self):
        """
        utils.get_channels('featured', True) should return a list
        of Channels that are currently featured.  False should return a list of
        Channels that are not featured.

        XXX: What should this do about the queue?
        """
        self.channels[1].featured = True
        self.channels[1].featured_by = self.owner
        self.channels[1].save()
        objs = utils.get_channels(self.make_request(), 'featured', True)
        self.assertEquals(len(objs), 1)
        self.assertEquals(objs[0].id, self.channels[1].id)

        objs2 = utils.get_channels(self.make_request(), 'featured', False)
        self.assertEquals(len(objs2), 1)
        self.assertEquals(objs2[0].id, self.channels[0].id)

    def test_get_channels_filter_hd(self):
        """
        utils.get_channels('hd', True) should return a list of
        Channels that are high-def.  False should return a list of Channels
        that are not high-def.
        """
        self.channels[1].hi_def = True
        self.channels[1].save()
        objs = utils.get_channels(self.make_request(), 'hd', True)
        self.assertEquals(len(objs), 1)
        self.assertEquals(objs[0].id, self.channels[1].id)

        objs2 = utils.get_channels(self.make_request(), 'hd', False)
        self.assertEquals(len(objs2), 1)
        self.assertEquals(objs2[0].id, self.channels[0].id)

    def test_get_channels_filter_feed(self):
        """
        utils.get_channels('feed', True) should return Channels
        that have a feed.  False should return a list of Channels that do not.
        """
        self.channels[1].url = None
        self.channels[1].save()
        objs = utils.get_channels(self.make_request(), 'feed', False)
        self.assertEquals(len(objs), 1)
        self.assertEquals(objs[0].id, self.channels[1].id)

        objs2 = utils.get_channels(self.make_request(), 'feed', True)
        self.assertEquals(len(objs2), 1)
        self.assertEquals(objs2[0].id, self.channels[0].id)

    def test_get_channels_filter_audio(self):
        """
        api.get_channels('audio', True) should return Channels that are marked
        as audio.  False should return a list of Channels that are not.
        """
        self.channels[1].state = self.channels[1].AUDIO
        self.channels[1].save()
        objs = utils.get_channels(self.make_request(), 'audio', True)
        self.assertEquals(len(objs), 1)
        self.assertEquals(objs[0].id, self.channels[1].id)

        objs2 = utils.get_channels(self.make_request(), 'audio', False)
        self.assertEquals(len(objs2), 1)
        self.assertEquals(objs2[0].id, self.channels[0].id)

    def test_get_channels_filter_search(self):
        self.channels[1].change_state(self.owner, 'N', )
        for channel in self.channels:
            ChannelSearchData.objects.update(channel)
        objs = utils.get_channels(self.make_request(), 'search', 'Channel')
        self.assertEquals(len(objs), 1)
        self.assertEquals(objs[0].id, self.channels[0].id)

    def test_get_channels_filter_search_as_moderator(self):
        self.owner.get_profile().promote()
        self.owner.get_profile().promote()
        self.channels[1].change_state(self.owner, 'N', )
        for channel in self.channels:
            ChannelSearchData.objects.update(channel)
        objs = utils.get_channels(self.make_request(), 'search', 'Channel')
        self.assertEquals(len(objs), 2)
        self.assertEquals(objs[0].id, self.channels[0].id)
        self.assertEquals(objs[1].id, self.channels[1].id)

    def test_get_channels_filter_hide_unapproved(self):
        """
        The default should be to only show approved channels.
        """
        self.channels[1].change_state(self.owner, 'N')
        objs = utils.get_channels(self.make_request(), 'name',
                                  self.channels[1].name)
        self.assertEquals(len(objs), 0)

    def test_get_channels_filter_search_unicode(self):
        unicode_name = u'\u6771\u68ee\u65b0\u805e'
        self.channels[0].name = unicode_name
        self.channels[0].save()
        ChannelSearchData.objects.update(self.channels[0])
        objs = utils.get_channels(self.make_request(), 'search', unicode_name)
        self.assertEquals(len(objs), 1)
        self.assertEquals(objs[0].id, self.channels[0].id)

    def test_get_channels_filter_multiple(self):
        self.channels.append(self.make_channel(self.owner, state='A'))
        self.channels[1].name = 'Testing Testing'
        self.channels[1].url = None
        self.channels[1].save()
        self.channels[2].name = 'Testing Testing'
        self.channels[2].save()

        objs = utils.get_channels(self.make_request(), 'feed', True)
        self.assertEquals(len(objs), 2)
        self.assertEquals(objs[0].id, self.channels[0].id)
        self.assertEquals(objs[1].id, self.channels[2].id)

        objs2 = utils.get_channels(self.make_request(), ('feed', 'name'),
                                (True, self.channels[2].name))
        self.assertEquals(len(objs2), 1)
        self.assertEquals(objs2[0].id, self.channels[2].id)

    def test_get_channels_sort_name(self):
        """
        Passing sort='name' to get_channels should sort the channels by their
        name.  Also, if no sort is specified, it should be sorted by name.
        """
        new = self.make_channel(self.owner, state='A')
        new.name = 'AAA'
        new.save()

        objs = utils.get_channels(self.make_request(), 'name', '', sort='name')
        self.assertSameChannels(objs, [new] + self.channels)

        objs = utils.get_channels(self.make_request(), 'name', '',
                                  sort='-name')
        self.assertSameChannels(objs, reversed([new] + self.channels))

        objs = utils.get_channels(self.make_request(), 'name', '')
        self.assertSameChannels(objs, [new] + self.channels)

        objs = utils.get_channels(self.make_request(), 'name', None)
        self.assertSameChannels(objs, [new] + self.channels)

    def test_get_channels_sort_id(self):
        """
        Passing sort='id' to get_channels should sort the channels by their
        id.
        """
        new = self.make_channel(self.owner, state='A')
        new.name = 'AAA'
        new.save()

        objs = utils.get_channels(self.make_request(), 'name', '', sort='id')
        self.assertSameChannels(objs, self.channels + [new])

        objs = utils.get_channels(self.make_request(), 'name', '', sort='-id')
        self.assertSameChannels(objs, reversed(self.channels + [new]))

    def test_get_channels_sort_age(self):
        """
        Passing sort='age' to get_channels should sort the channels by their
        approval date.
        """
        new = self.make_channel(self.owner, state='A')
        new.approved_at = datetime.min.replace(year=1900)
        new.save()

        objs = utils.get_channels(self.make_request(), 'name', '', sort='age')
        self.assertEquals(objs[-1].id, new.id)

        objs = utils.get_channels(self.make_request(), 'name', '', sort='-age')
        self.assertEquals(objs[0].id, new.id)

    def test_get_channels_sort_popular(self):
        """
        Passing sort='popular' to get_channels should sort the channels by
        their popularity.
        """
        new = self.make_channel(self.owner, state='A')
        Subscription.objects.add(new, '2.2.2.2',
                                 datetime.now() - timedelta(seconds=5))
        Subscription.objects.add(new, '1.1.1.1')

        call_command('refresh_stats_table')

        objs = utils.get_channels(self.make_request(), 'name', '',
                                  sort='popular')
        self.assertEquals(objs[-1].id, new.id)

        objs = utils.get_channels(self.make_request(), 'name', '',
                                  sort='-popular')
        self.assertEquals(objs[0].id, new.id)

    def test_get_channels_sort_rating(self):
        """
        Passing sort='rating' to get_channels should sort the channels by
        their rating.
        """
        new = self.make_channel(self.owner, state='A')
        for i in range(6):
            # make some fake ratings so that all the channels have 6 ratings
            fake = self.make_user('fake%i' % i)
            fake.get_profile().approved = True
            fake.get_profile().save()
            for channel in self.channels:
                rating, created = Rating.objects.get_or_create(channel=channel,
                                                               user=fake)
                rating.rating = 3
                rating.save()
            rating, created = Rating.objects.get_or_create(channel=new,
                                                           user=fake)
            rating.rating = 3
            rating.save()
        self.owner.get_profile().approved = True
        self.owner.get_profile().save()
        rating, created = Rating.objects.get_or_create(channel=new,
                                                       user=self.owner)
        rating.rating = 5
        rating.save()

        objs = utils.get_channels(self.make_request(), 'name', '',
                                  sort='rating')
        self.assertEquals(objs[-1].id, new.id)

        objs = utils.get_channels(self.make_request(), 'name', '',
                                  sort='-rating')
        self.assertEquals(objs[0].id, new.id)

    def test_get_channels_limit(self):
        """
        Passing a limit kwarg to get_channels should limit the number of
        channels that are returned.
        """
        objs = utils.get_channels(self.make_request(), 'name', '', limit=1)
        self.assertEquals(len(objs), 1)
        self.assertEquals(objs[0].id, self.channels[0].id)

    def test_get_channels_offset(self):
        """
        Passing an offset kwarg to get_channels should skip that number of
        channels.
        """
        objs = utils.get_channels(self.make_request(), 'name', '', offset=1)
        self.assertEquals(len(objs), 1)
        self.assertEquals(objs[0].id, self.channels[1].id)

    def test_get_channels_archived_sorted_last(self):
        """
        Regardless of any sorting options, archived channels should be sorted
        after all non-archived channels.
        """
        new = self.make_channel(self.owner, state='A')
        new.name = 'AAA'
        new.archived = True
        new.save()

        objs = utils.get_channels(self.make_request(), 'name', '', sort='name')
        self.assertSameChannels(objs, self.channels + [new])

        objs = utils.get_channels(self.make_request(), 'name', '',
                                  sort='-name')
        self.assertSameChannels(objs, list(reversed(self.channels)) + [new])

    def test_search(self):
        """
        utils.search('query') should return a list of Channels
        which match the search criteria.
        """
        for channel in self.channels:
            ChannelSearchData.objects.update(channel)
        objs = utils.search(['description'])
        self.assertEquals(len(objs), 1)
        self.assertEquals(objs[0].id, self.channels[1].id)

    def test_get_rating(self):
        """
        utils.get_rating(user, channel) should return the rating
        the user gave the channel, or none if it hasn't been rated.
        """
        self.assertEquals(utils.get_rating(self.owner,
                                         self.channels[0]), None)
        rating, created = Rating.objects.get_or_create(
            channel=self.channels[0], user=self.owner)
        rating.rating = 5
        rating.save()

        self.assertEquals(utils.get_rating(self.owner,
                                         self.channels[0]), 5)

    def test_get_ratings(self):
        """
        utils.get_ratings(user) should return the ratings the
        user has given.
        """
        rating, created = Rating.objects.get_or_create(
            channel=self.channels[0], user=self.owner)
        rating.rating = 5
        rating.save()
        rating, created = Rating.objects.get_or_create(
            channel=self.channels[1], user=self.owner)
        rating.rating = 4
        rating.save()

        self.assertEquals(utils.get_ratings(self.owner),
                          {self.channels[0]: 5,
                           self.channels[1]: 4
                           })

    def test_get_ratings_filter(self):
        """
        utils.get_ratings(user, rating=<value>) should return a
        list of the channels with that rating.
        """
        rating, created = Rating.objects.get_or_create(
            channel=self.channels[0], user=self.owner)
        rating.rating = 5
        rating.save()
        rating, created = Rating.objects.get_or_create(
            channel=self.channels[1], user=self.owner)
        rating.rating = 4
        rating.save()

        self.assertEquals(utils.get_ratings(self.owner,
                                          rating=5),
                          self.channels[:1])

    def test_get_recommendations(self):
        rating, created = Rating.objects.get_or_create(
            channel=self.channels[0], user=self.owner)
        rating.rating = 5
        rating.save()

        call_command('refresh_stats_table')
        call_command('calculate_recommendations')

        channels = utils.get_recommendations(self.owner)
        self.assertEquals(len(channels), 1)
        self.assertEquals(channels[0].id, self.channels[1].id)
        self.assertEquals(channels[0].guessed, 5.0)
        self.assertEquals(len(channels[0].reasons), 1)
        self.assertEquals(channels[0].reasons[0].id, self.channels[0].id)
        self.assertTrue(channels[0].reasons[0].score > 0.5)


    def test_list_categories(self):
        categories = utils.list_labels('category')
        self.assertEquals(len(categories), 2)
        self.assertEquals(categories[0].id, self.categories[0].id)
        self.assertEquals(categories[1].id, self.categories[1].id)

    def test_list_languages(self):
        languages = utils.list_labels('language')
        self.assertEquals(len(languages), 3)
        self.assertEquals(languages[0].id, self.language.id)
        self.assertEquals(languages[1].id, self.languages[0].id)
        self.assertEquals(languages[2].id, self.languages[1].id)
