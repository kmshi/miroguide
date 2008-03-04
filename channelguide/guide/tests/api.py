from datetime import datetime

from channelguide.guide.models import ApiKey, Category, Item, Language, Tag
from channelguide.testframework import TestCase
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

    def test_get_channel(self):
        """
        /api/get_channel should return the information for a channel given
        its id.
        """
        channel = self.channels[0]
        response = self.make_api_request('get_channel', id=channel.id)
        self.assertEquals(response.status_code, 200)
        print response.content
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

class ChannelApiFunctionTest(ChannelApiTestBase):

    def test_get_channel(self):
        """
        api.get_channel(conection, id) should return a full channel object, with
        categories, tags, and items.
        """
        obj = api.get_channel(self.connection, self.channels[0].id)
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
