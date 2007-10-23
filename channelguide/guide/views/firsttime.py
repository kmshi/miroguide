from channelguide import cache, util, settings
from channelguide.guide.views import frontpage, channels
from channelguide.guide.models import Channel, Category

@cache.aggresively_cache
@cache.cache_page_externally_for(3600)
def index(request):
    faqs = [
            ("I don't get it &mdash; what does Miro do?", 'Answer 1'),
            ('Will my hard drive fill up with videos?', 'Answer 2'),
            ('What is a channel?', 'Answer 3'),
            ('How do I delete channels?', 'Answer 4'),
            ('When is Miro the best way to watch videos?', 'Answer 5'),
            ('How can I find channels I want to watch?', 'Answer 6'),
            ]
    popular = frontpage.get_popular_channels(request.connection, 5)
    toprated = channels.get_toprated_query().limit(5).execute(request.connection)
    channel_columns = [
            [('Popular', popular), ('Top Rated', toprated)]]
    popular_categories = iter(Category.query().load('channel_count').order_by('channel_count', desc=True).execute(request.connection))
    for i in range(3):
        category_channels = []
        for j in range(2):
            cat = popular_categories.next()
            name = cat.name
            query = Channel.query_approved().join('categories')
            query.joins['categories'].where(id=cat.id)
            query.limit(5)
            query.cacheable = cache.client
            query.cacheable_time = 3600
            category_channels.append((name, query.execute(request.connection)))
        channel_columns.append(category_channels)
    return util.render_to_response(request, 'firsttime.html',
            { 'faqs': faqs,
              'channel_columns': channel_columns,
              'MOVIE_URL':'http://blip.tv/file/get/Miropcf-UnwatchAnyVideo407.mp4',
              })
