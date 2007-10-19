from channelguide import cache, util, settings
from channelguide.guide.views import frontpage, channels
from channelguide.guide.models import Channel, Category

@cache.aggresively_cache
@cache.cache_page_externally_for(3600)
def index(request):
    faqs = [
            ('Question 1?', 'Answer 1'),
            ('Question 2?', 'Answer 2'),
            ('Question 3?', 'Answer 3'),
            ('Question 4?', 'Answer 4'),
            ('Question 5?', 'Answer 5'),
            ('Question 6?', 'Answer 6'),
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
            category_channels.append((name, query.execute(request.connection)))
        channel_columns.append(category_channels)
    return util.render_to_response(request, 'firsttime.html',
            { 'faqs': faqs,
              'channel_columns': channel_columns,
              'MOVIE_URL':'http://blip.tv/file/get/Miropcf-UnwatchAnyVideo407.mp4',
              })
