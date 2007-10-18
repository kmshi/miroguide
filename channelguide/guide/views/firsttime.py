from channelguide import cache, util

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
    return util.render_to_response(request, 'firsttime.html',
            { 'faqs': faqs})
