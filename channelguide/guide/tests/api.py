from datetime import datetime, timedelta
import simplejson

from channelguide.guide.models import ApiKey, Category, Item, Language, Tag
from channelguide.testframework import TestCase
from channelguide import manage, sessions
from channelguide.guide import api
from channelguide.guide.tests.channels import test_data_path

class ChannelApiTestBase(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.owner = self.make_user('owner')
        self.owner.save(self.connection)
        self.channels = []
        for i in range(2):
            channel = self.make_channel(self.owner, state='A')
            channel.name = 'My Channel %i' % i
            channel.save(self.connection)
            self.channels.append(channel)
        categories = []
        languages = []
        items = []
        for n in range(2):
            cat = Category('category%i' % n)
            cat.save(self.connection)

            lang = Language('language%i' % n)
            lang.save(self.connection)

            item = Item()
            item.channel_id = self.channels[0].id
            item.url = self.channels[0].url
            item.name = 'item%i' % n
            item.description = 'Item'
            item.size = i
            item.date = datetime.now()
            item.save(self.connection)
            item.save_thumbnail(self.connection,
                    file(test_data_path('thumbnail.jpg')).read())

            categories.append(cat)
            languages.append(lang)
            items.append(item)
        self.channels[0].join('categories',
                'secondary_languages').execute(self.connection)
        self.channels[0].categories.add_records(self.connection, categories)
        self.channels[0].primary_language_id = languages[0].id
        self.channels[0].secondary_languages.add_record(self.connection,
                languages[1])
        self.channels[0].add_tags(self.connection, self.owner, ['tag0', 'tag1'])
        self.channels[0].save_thumbnail(self.connection,
                file(test_data_path('thumbnail.jpg')).read())

        self.channels[1].description = 'This is a different description.'
        self.channels[1].save(self.connection)
        self.channels[0].add_subscription(self.connection, '123.123.123.123',
                                          datetime.now())
        self.channels[1].add_subscription(self.connection, '123.123.123.123',
                                          datetime.now() + timedelta(days=1))

        
class ChannelApiViewTest(ChannelApiTestBase):

    def setUp(self):
        ChannelApiTestBase.setUp(self)
        key = ApiKey.new(self.owner.id, '')
        key.save(self.connection)
        self.key = key.api_key
        self.refresh_connection()

    def make_api_request(self, request, **kw):
        url = '/api/' + request
        kw['key'] = self.key
        return self.get_page(url, data=kw)

    def test_missing_key_401(self):
        """
        Requesting an API method without a key should return a 400 response.
        """
        response = self.get_page('/api/test',
                data={'id': 0 })
        self.assertEquals(response.status_code, 400)

    def test_invalid_key_401(self):
        """
        Requesting an API method with a key that doesn't exist or isn't active
        should return a 403 error.
        """
        response = self.get_page('/api/test',
                data={'key': '0'*20})
        self.assertEquals(response.status_code, 403)

        key = ApiKey.new(self.owner.id, '')
        key.active = False
        key.save(self.connection)
        self.refresh_connection()
        response = self.get_page('/api/test',
                data={'key': key.api_key})
        self.assertEquals(response.status_code, 403)

    def test_valid_key_200(self):
        """
        Making a request with a valid API key should return a 200 response.
        """
        response = self.get_page('/api/test', data={'key': self.key})
        self.assertEquals(response.status_code, 200, response.content)
        self.assertEquals(eval(response.content),
                {'text': 'Valid API key'})

    def test_json_response(self):
        """
        Making a request with datatype=json should return a JSON object instead
        of a Python object.
        """
        response = self.get_page('/api/test', data={'key': self.key,
                                                    'datatype': 'json'})
        self.assertEquals(simplejson.loads(response.content),
                          {'text': 'Valid API key'})

    def test_json_callback(self):
        """
        A request with datatype=json and jsoncallback=<function name> should
        return a string which calls the given function with the data.
        """
        response = self.get_page('/api/test', data={'key': self.key,
                                                    'datatype': 'json',
                                                    'jsoncallback': 'foo'})
        content = response.content
        self.assertTrue(content.startswith('foo('))
        self.assertTrue(content.endswith(');'))
        self.assertEquals(simplejson.loads(response.content[4:-2]),
                          {'text': 'Valid API key'})
        
    def _verifyChannelResponse(self, response, channel):
        self.assertEquals(response.status_code, 200)

        data = eval(response.content)
        self.assertEquals(data['id'], channel.id)
        self.assertEquals(data['name'], channel.name)
        self.assertEquals(data['description'], channel.description)
        self.assertEquals(data['url'], channel.url)
        self.assertEquals(data['website_url'], channel.website_url)
        self.assertEquals(data['language'], ('language0', 'language1'))
        self.assertEquals(data['category'], ('category0', 'category1'))
        self.assertEquals(data['tag'], ('tag0', 'tag1'))
        self.assert_('thumbnail_url' in data)
        self.assertEquals(len(data['item']), 2)
        for i in range(2):
            item = data['item'][i]
            self.assertEquals(item['name'], 'item%i' % i)
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
        channel = self.channels[0]
        response = self.make_api_request('get_channel', id=channel.id)
        self._verifyChannelResponse(response, channel)

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
        
    def test_get_channels(self):
        response = self.make_api_request('get_channels', filter='category',
            filter_value='category0')
        self.assertEquals(response.status_code, 200)
        data = eval(response.content)
        self.assert_(isinstance(data, list))
        self.assertEquals(data[0]['id'], self.channels[0].id)
        self.assertEquals(data[0].get('category'), None)

    def test_get_session(self):
        response = self.make_api_request('get_session')
        self.assertEquals(response.status_code, 200)
        data = eval(response.content)
        self.assertEquals(len(data['session']), 32)

    def _do_authentication(self,  response):
        self.assertEquals(response.status_code, 200)
        context = response.context[0]
        self.assertEquals(context['key'], self.key)

        data = {'key': context['key'],
              'verification': context['verification']
              }
        if context.get('session'):
            data['session'] = context['session']
        if context.get('redirect'):
            data['redirect'] = context['redirect']
            
        return self.post_data('/api/authenticate', data, self.owner)

    def _get_session(self):
        response = self.get_page('/api/authenticate', self.owner,
                                 {'key': self.key})
        response = self._do_authentication(response)
        return response.context[0]['session']
    
    def test_authenticate(self):
        response = self.get_page('/api/authenticate', self.owner, {
                'key': self.key,
                'redirect': 'http://test.com/'})
        context = response.context[0]
        self.assertEquals(context['session'], None)
        self.assertEquals(context['redirect'], 'http://test.com/')        
        response = self._do_authentication(response)
        self.assertRedirect(response, 'http://test.com/')
        self.assert_('?session=' in response['Location'])
        session = sessions.util.get_session_from_key(self.connection,
                                                response['Location'][-32:])
        data = session.get_data()
        self.assertEquals(data['key'], self.key)
        self.assertEquals(data['apiUser'], self.owner.id)
        

    def test_authenticate_without_redirect(self):
        response = self.get_page('/api/authenticate', self.owner, {
                'key': self.key})
        response = self._do_authentication(response)
        self.assertEquals(response.context[0]['success'], True)

    def test_authenticate_with_session(self):
        sessionID = sessions.util.make_new_session_key(self.connection)
        response = self.get_page('/api/authenticate', self.owner,
                                 {'key': self.key,
                                  'redirect': 'http://test.com/',
                                  'session': sessionID})
        response = self._do_authentication(response)
        self.assertRedirect(response, 'http://test.com/')
        self.assertEquals(response['Location'], 'http://test.com/?session=%s'
                            % sessionID)

    def test_authenticate_not_verified(self):
        response = self.post_data('/api/authenticate', {'key': self.key,
                                  'verification': 'foo'}, self.owner)
        self.assertNotEquals(response.context[0].get('error'), None)

    def test_authenticate_invalid_key_404(self):
        response = self.get_page('/api/authenticate', self.owner,
                                 {'key': 'invalid key'})
        self.assertEquals(response.status_code, 404)
        
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
        self.channels[0].rate(self.connection, self.owner, 5)
        self.channels[1].rate(self.connection, self.owner, 4)
        self.refresh_connection()
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
        self.channels[0].rate(self.connection, self.owner, 5)
        self.channels[1].rate(self.connection, self.owner, 4)
        self.refresh_connection()
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
        self.channels[0].rate(self.connection, self.owner, 5)
        self.refresh_connection()
        manage.refresh_stats_table()
        manage.calculate_recommendations([None, None, 'full'])
        self.refresh_connection()
        response = self.make_api_request('get_recommendations',
                                         session=session)
        self.assertEquals(response.status_code, 200)
        data = eval(response.content)
        self.assertEquals(len(data), 1)
        self.assertEquals(data[0]['id'], self.channels[1].id)
        self.assertEquals(data[0]['guessed'], 5.0)
        self.assertEquals(len(data[0]['reasons']), 1)
        self.assertEquals(data[0]['reasons'][0]['id'], self.channels[0].id)
        self.assertEquals(data[0]['reasons'][0]['score'], 0.625)
        
        
class ChannelApiFunctionTest(ChannelApiTestBase):

    def assertSameChannels(self, l1, l2):
        self.assertEquals([c.id for c in l1], [c.id for c in l2])

    def test_get_channel(self):
        """
        api.get_channel(conection, id) should return a full channel object, with
        categories, tags, and items.
        """
        obj = api.get_channel(self.connection, self.channels[0].id)
        self.assertEquals(obj.id, self.channels[0].id)
        self.assertEquals(obj.url, self.channels[0].url)
        self.assertEquals(obj.owner.username, 'owner')
        self.assertEquals(len(obj.categories), 2)
        self.assertEquals(len(obj.tags), 2)
        self.assertEquals(len(obj.items), 2)

    def test_get_channel_by_url(self):
        """
        api.get_channel_by_url(connection, url0 should return a full channel
        object with categories, tags, and items.
        """
        obj = api.get_channel_by_url(self.connection, self.channels[0].url)
        self.assertEquals(obj.id, self.channels[0].id)
        self.assertEquals(obj.url, self.channels[0].url)
        self.assertEquals(obj.owner.username, 'owner')
        self.assertEquals(len(obj.categories), 2)
        self.assertEquals(len(obj.tags), 2)
        self.assertEquals(len(obj.items), 2)
        
    def test_get_channels_filter_category(self):
        """
        api.get_channels(connection, 'category', 'category name') should
        return a list of Channels that belong to that category.
        """
        objs = api.get_channels(self.connection, 'category', 'category0')
        self.assertEquals(len(objs), 1)
        self.assertEquals(objs[0].id, self.channels[0].id)

        objs2 = api.get_channels(self.connection, 'category', 'unknown')
        self.assertEquals(len(objs2), 0)

    def test_get_channels_filter_tag(self):
        """
        api.get_channels(connection, 'tag', 'tag name') should
        return a list of Channels that belong to that category.
        """
        objs = api.get_channels(self.connection, 'tag', 'tag0')
        self.assertEquals(len(objs), 1)
        self.assertEquals(objs[0].id, self.channels[0].id)

        objs2 = api.get_channels(self.connection, 'tag', 'unknown')
        self.assertEquals(len(objs2), 0)

    def test_get_channels_filter_language(self):
        """
        api.get_channels(connection, 'language', 'language name') should
        return a list of Channels that belong to that category.
        """
        objs = api.get_channels(self.connection, 'language', 'language0')
        self.assertEquals(len(objs), 1)
        self.assertEquals(objs[0].id, self.channels[0].id)

        # secondary language
        objs2 = api.get_channels(self.connection, 'language', 'language1')
        self.assertEquals(len(objs2), 1)
        self.assertEquals(objs2[0].id, self.channels[0].id)

        objs3 = api.get_channels(self.connection, 'language', 'unknown')
        self.assertEquals(len(objs3), 0)

    def test_get_channels_sort_name(self):
        """
        Passing sort='name' to get_channels should sort the channels by their
        name.  Also, if no sort is specified, it should be sorted by name.
        """
        new = self.make_channel(self.owner, state='A')
        new.name = 'AAA'
        new.save(self.connection)

        objs = api.get_channels(self.connection, 'name', '', sort='name')
        self.assertSameChannels(objs, [new] + self.channels)

        objs = api.get_channels(self.connection, 'name', '', sort='-name')
        self.assertSameChannels(objs, reversed([new] + self.channels))

        objs = api.get_channels(self.connection, 'name', '')
        self.assertSameChannels(objs, [new] + self.channels)

    def test_get_channels_sort_id(self):
        """
        Passing sort='id' to get_channels should sort the channels by their
        id.
        """
        new = self.make_channel(self.owner, state='A')
        new.name = 'AAA'
        new.save(self.connection)

        objs = api.get_channels(self.connection, 'name', '', sort='id')
        self.assertSameChannels(objs, self.channels + [new])

        objs = api.get_channels(self.connection, 'name', '', sort='-id')
        self.assertSameChannels(objs, reversed(self.channels + [new]))

    def test_get_channels_sort_age(self):
        """
        Passing sort='age' to get_channels should sort the channels by their
        approval date.
        """
        new = self.make_channel(self.owner, state='A')
        new.approved_at = datetime.min.replace(year=1900)
        new.save(self.connection)

        objs = api.get_channels(self.connection, 'name', '', sort='age')
        self.assertEquals(objs[-1].id, new.id)

        objs = api.get_channels(self.connection, 'name', '', sort='-age')
        self.assertEquals(objs[0].id, new.id)

    def test_get_channels_sort_popular(self):
        """
        Passing sort='popular' to get_channels should sort the channels by
        their popularity.
        """
        new = self.make_channel(self.owner, state='A')
        new.add_subscription(self.connection, '2.2.2.2',
                             timestamp = datetime.now() - timedelta(seconds=5))
        new.add_subscription(self.connection, '1.1.1.1')
        self.refresh_connection()
        manage.refresh_stats_table()
        self.refresh_connection()

        objs = api.get_channels(self.connection, 'name', '', sort='popular')
        self.assertEquals(objs[-1].id, new.id)

        objs = api.get_channels(self.connection, 'name', '', sort='-popular')
        self.assertEquals(objs[0].id, new.id)

    def test_get_channels_sort_rating(self):
        """
        Passing sort='rating' to get_channels should sort the channels by
        their rating.
        """
        self.owner.approved = True
        self.owner.save(self.connection)
        new = self.make_channel(self.owner, state='A')
        new.rate(self.connection, self.owner, 5)

        objs = api.get_channels(self.connection, 'name', '', sort='rating')
        self.assertEquals(objs[-1].id, new.id)

        objs = api.get_channels(self.connection, 'name', '', sort='-rating')
        self.assertEquals(objs[0].id, new.id)

    def test_get_channels_limit(self):
        """
        Passing a limit kwarg to get_channels should limit the number of
        channels that are returned.
        """
        objs = api.get_channels(self.connection, 'name', '', limit=1)
        self.assertEquals(len(objs), 1)
        self.assertEquals(objs[0].id, self.channels[0].id)

    def test_get_channels_offset(self):
        """
        Passing an offset kwarg to get_channels should skip that number of
        channels.
        """
        objs = api.get_channels(self.connection, 'name', '', offset=1)
        self.assertEquals(len(objs), 1)
        self.assertEquals(objs[0].id, self.channels[1].id)

    def test_search(self):
        """
        api.search(connection, 'query') should return a list of Channels
        which match the search criteria.
        """
        for channel in self.channels:
            channel.update_search_data(self.connection)
        objs = api.search(self.connection, ['description'])
        self.assertEquals(len(objs), 1)
        self.assertEquals(objs[0].id, self.channels[1].id)

    def test_get_rating(self):
        """
        api.get_rating(connection, user, channel) should return the rating
        the user gave the channel, or none if it hasn't been rated.
        """
        self.assertEquals(api.get_rating(self.connection, self.owner,
                                         self.channels[0]), None)
        self.channels[0].rate(self.connection, self.owner, 5)
        self.assertEquals(api.get_rating(self.connection, self.owner,
                                         self.channels[0]), 5)

    def test_get_ratings(self):
        """
        api.get_ratings(connection, user) should return the ratings the
        user has given.
        """
        self.channels[0].rate(self.connection, self.owner, 5)
        self.channels[1].rate(self.connection, self.owner, 4)
        self.assertEquals(api.get_ratings(self.connection, self.owner),
                          {self.channels[0]: 5,
                           self.channels[1]: 4
                           })

    def test_get_ratings_filter(self):
        """
        api.get_ratings(connection, user, rating=<value>) should return a list
        of the channels with that rating.
        """
        self.channels[0].rate(self.connection, self.owner, 5)
        self.channels[1].rate(self.connection, self.owner, 4)
        self.assertEquals(api.get_ratings(self.connection, self.owner,
                                          rating=5),
                          self.channels[:1])
                          
    def test_get_recommendations(self):
        self.channels[0].rate(self.connection, self.owner, 5)
        self.refresh_connection()
        manage.refresh_stats_table()
        manage.calculate_recommendations([None, None, 'full'])
        self.refresh_connection()
        channels = api.get_recommendations(self.connection, self.owner)
        self.assertEquals(len(channels), 1)
        self.assertEquals(channels[0].id, self.channels[1].id)
        self.assertEquals(channels[0].guessed, 5.0)
        self.assertEquals(len(channels[0].reasons), 1)
        self.assertEquals(channels[0].reasons[0].id, self.channels[0].id)
        self.assertEquals(channels[0].reasons[0].score, 0.625)

        
class ChannelApiManageTest(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.admin = self.make_user('admin', role='A')

    def _make_key(self):
        key = ApiKey.new(self.admin.id, '')
        key.save(self.connection)
        self.refresh_connection()
        return key

    def test_add(self):
        """
        Sending an add request should create an ApiKey with the given owner id
        and description.
        """
        data = {'action': 'add',
                'owner': 'admin',
                'description': 'description of the key'}
        self.post_data('/api/manage', data, self.admin)
        keys = ApiKey.query().execute(self.connection)
        self.assertEquals(len(keys), 1)
        key = keys[0]
        self.assertEquals(key.owner_id, self.admin.id)
        self.assertEquals(key.description, data['description'])

    def test_toggle_active(self):
        """
        Sending a toggle-active request should toggle the active bit on the
        key.
        """
        key = self._make_key()
        data = {'action': 'toggle-active',
                'key': key.api_key}
        self.post_data('/api/manage', data, self.admin)
        updated = self.refresh_record(key)
        self.assertEquals(updated.active, False)

        self.post_data('/api/manage', data, self.admin)
        updated = self.refresh_record(key)
        self.assertEquals(updated.active, True)
