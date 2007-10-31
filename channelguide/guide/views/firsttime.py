from urllib import urlencode
from channelguide import cache, util, settings
from channelguide.guide.views import frontpage, channels
from channelguide.guide.models import Channel, Category

@cache.aggresively_cache
@cache.cache_page_externally_for(3600)
def index(request):
    channel_packs = [
            [
                ('Movies/TV',
                    'http://www.kqed.org/rss/private/spark.xml',
                    'http://feeds.feedburner.com/theburg',
                    'http://www.atomfilms.com/rss/atomtogo.xml',
                    'http://files.myopera.com/TimoP/files/timostrailers.rss',
                    'http://www.archiveclassicmovies.com/democracy.xml',
                    'http://www.sesameworkshop.org/podcasts/sesamestreet/rss.xml'),
                ('Sports',
                    'http://sports.espn.go.com/espnradio/podcast/feeds/itunes/podCast?id=2870570',
                    'http://feeds.foxnews.com/podcasts/FightGame',
                    'http://www.bleacherbloggers.com/rss',
                    'http://www.sportal.com.au/podcast/sportalcomau_rss.xml',
                    'http://www.onnetworks.com/videos/shows/1699/podcast/hd'
                )
            ],
            [
                ('Music',
                    'http://www.telemusicvision.com/videos/rss.php?i=1',
                    'http://revision3.com/notmtv/feed/quicktime-large',
                    'http://feeds.feedburner.com/theswitched',
                    'http://feeds.feedburner.com/volcast',
                    'http://abcnews.go.com/xmldata/xmlPodcast?id=1456635&src=i'),
                ('Tech',
                    'http://feeds.feedburner.com/TEDTalks_video',
                    'http://revision3.com/tekzilla/feed/quicktime-high-definition',
                    'http://jetset.blip.tv/?skin=rss',
                    'http://www.podshow.com/feeds/gbtv.xml',
                    'http://revision3.com/diggnation/feed/quicktime-large',
                    'http://feeds.feedburner.com/webbalert')
            ],
            [
                ('Science',
                    'http://feeds.feedburner.com/Terravideos',
                    'http://www.pbs.org/wnet/nature/rss/podcast.xml',
                    'http://podcast.nationalgeographic.com/wild-chronicles/',
                    'http://krampf.blip.tv/rss',
                    'http://www.discovery.com/radio/xml/sciencevideo.xml',
                    'http://www.discovery.com/radio/xml/discovery_video.xml'),
                ('Entertainment',
                    'http://feeds.boingboing.net/boingboing/tv',
                    'http://revision3.com/webdrifter/feed/quicktime-high-definition',
                    'http://feeds.theonion.com/OnionNewsNetwork',
                    'http://feeds.feedburner.com/AskANinja',
                    'http://www.channelfrederator.com/rss',
                    'http://feeds.feedburner.com/classicanimation')
            ],
            [
                ('News',
                    'http://feeds.cbsnews.com/podcast_eveningnews_video_1.rss',
                    'http://abcnews.go.com/xmldata/xmlPodcast?id=1478958&src=i',
                    'http://podcast.msnbc.com/audio/podcast/MSNBC-NN-NETCAST-M4V.xml',
                    'http://www.democracynow.org/podcast-video.xml',
                    'http://submedia.tv/submediatv/bm/rss/2',
                    'http://www.rocketboom.com/vlog/rb_hd.xml'
                ),
                ('Food',
                    'http://www.epicurious.com/services/rss/feeds/sitewide_podcast.xml',
                    'http://aww.ninemsn.com.au/podcast/freshtv/video/',
                    'http://www.simplyming.org/rss/vodcast.xml',
                    'http://www.foodguru.com/podcast/xml.xml',
                    'http://feeds.feedburner.com/averagebetty_itunes_video')
            ]
        ]
    faqs = [
            ("I don't get it &mdash; what does Miro do?", """<p>Miro is a fresh concept for internet TV -- instead of visiting a ton of different websites to watch videos, the videos come to you from all over the internet, organized as channels.  When you find a channel you like, add it to Miro. The second a new episode is available, it'll be downloaded.</p>"""),
            ('Will my hard drive fill up with videos?', """<p>Once you watch a video, Miro will set it to expire. Once a video expires, Miro deletes it to free up space on your hard drive.  Furthermore, there is a preference to disable downloads, if your drive space ever dips below a certain level.</p>"""),
            ('What is a channel?', """<p>Miro takes advantage of an existing standard (RSS) to create channels -- it's very similar to podcasting.  Because RSS is an open standard, there are lots of channels on the internet that aren't in the Miro Guide. You can easily add external channels via the 'add channel' menu option.</p>"""),
            ('How do I delete channels?', """You can remove a channel by right clicking (ctrl + click on Mac) any channel and choosing 'Remove Channel'."""),
            ('When is Miro the best way to watch videos?', """<p><strong>Regular Shows</strong>: When you find a channel you like, Miro saves you time -- no repeated trips to a website for updates, Miro will automatically download the latest videos as soon as they are available (schedules vary by individual publisher).</p>
<p><strong>Fullscreen</strong>: Miro is perfect when you want to watch longer form or more serious video -- put Miro in fullscreen mode, lean back, and enjoy your internet TV.</p>
<p><strong>Picture Quality</strong>: Your computer screen can display a sharper image than most TV sets. YouTube cannot take advantage of this fact (they only stream video), but Miro was designed to handle HD (High Definition) video. More and more creators are publishing their channels in HD. Miro is the best way to take advantage.</p>"""),
            ('How can I find channels I want to watch?', """<p>We keep track of popular and top rated channels in the Miro Guide. You can also browse by category or language.  In the near future, the Miro Guide will give personalized recommendations, based on the way you rate channels. Any ratings you leave now will count towards this feature.</p>"""),
            ]
    channel_columns = [[(column[0], util.get_subscription_url(*column[1:]))
        for column in row] for row in channel_packs]
    return util.render_to_response(request, 'firsttime.html',
            { 'faqs': faqs,
              'channel_columns': channel_columns,
              'MOVIE_URL':'http://blip.tv/file/get/Miropcf-MeetMiro299.mp4',
              })
