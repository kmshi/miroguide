from urllib import urlencode
from channelguide import cache, util, settings
from channelguide.guide.views import frontpage, channels
from channelguide.guide.models import Channel, Category

def _oneclick_url(channels):
    return util.get_subscription_url(*[channel.url for channel in channels])

@cache.aggresively_cache
@cache.cache_page_externally_for(3600)
def index(request):
    faqs = [
            ("I don't get it &mdash; what does Miro do?", """<p>Miro is a fresh concept for internet TV -- instead of visiting a ton of different websites to watch videos, the videos come to you from all over the internet, organized as channels.</p>
<p>When you find a channel you like, add it to Miro. The second a new episode is available, it'll be downloaded</p>"""),
            ('Will my hard drive fill up with videos?', """<p>Once you watch a video, Miro will set it to expire. Once a video expires, Miro deletes it to free up space on your hard drive.</p>
<p>Furthermore, there is a preference to disable downloads, if your drive space ever dips below a certain level.</p>"""),
            ('What is a channel?', """<p>Miro takes advantage of an existing standard (RSS) to create channels -- it's very similar to podcasting.</p>
<p>Because RSS is an open standard, there are lots of channels on the internet that aren't in the Miro Guide. You can easily add external channels via the 'add channel' menu option.</p>"""),
            ('How do I delete channels?', """You can remove a channel by right clicking (ctrl + click on Mac) any channel and choosing 'Remove Channel'."""),
            ('When is Miro the best way to watch videos?', """<p><strong>Regular Shows</strong>: When you find a channel you like, Miro saves you time -- no repeated trips to a website for updates, Miro will automatically download the latest videos as soon as they are available (schedules vary by individual publisher).</p>
<p><strong>Fullscreen</strong>: Miro is perfect when you want to watch longer form or more serious video -- put Miro in fullscreen mode, lean back, and enjoy your internet TV.</p>
<p><strong>Picture Quality</strong>: Your computer screen can display a sharper image than most TV sets. YouTube cannot take advantage of this fact (they only stream video), but Miro was designed to handle HD (High Definition) video. More and more creators are publishing their channels in HD. Miro is the best way to take advantage.</p>"""),
            ('How can I find channels I want to watch?', """<p>We keep track of popular and top rated channels in the Miro Guide. You can also browse by category or language.</p>
<p>In the near future, the Miro Guide will give personalized recommendations, based on the way you rate channels. Any ratings you leave now will count towards this feature.</p>"""),
            ]
    popular = _oneclick_url(frontpage.get_popular_channels(request.connection, 5))
    toprated = _oneclick_url(channels.get_toprated_query().limit(5).execute(request.connection))
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
            category_channels.append((name.split()[0], _oneclick_url(query.execute(request.connection))))
        channel_columns.append(category_channels)
    return util.render_to_response(request, 'firsttime.html',
            { 'faqs': faqs,
              'channel_columns': channel_columns,
              'MOVIE_URL':'http://blip.tv/file/get/Miropcf-UnwatchAnyVideo407.mp4',
              })
