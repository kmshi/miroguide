# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from urllib import urlencode
from channelguide import cache, util, settings
from channelguide.guide.views import frontpage, channels
from channelguide.guide.models import Channel, Category

@cache.aggresively_cache
@cache.cache_page_externally_for(3600)
def index(request):
    channel_packs = [
            [
                ('Sports', 'sports.png',
                    'http://sports.espn.go.com/espnradio/podcast/feeds/itunes/podCast?id=2870570',
                    'http://feeds.foxnews.com/podcasts/FightGame',
                    'http://www.bleacherbloggers.com/rss',
                    'http://www.sportal.com.au/podcast/sportalcomau_rss.xml',
                    'http://www.onnetworks.com/videos/shows/1699/podcast/hd'
                ),
                ('Movies/TV', 'moviesTV.png',
                    'http://www.kqed.org/rss/private/spark.xml',
                    'http://feeds.feedburner.com/theburg',
                    'http://www.atomfilms.com/rss/atomtogo.xml',
                    'http://files.myopera.com/TimoP/files/timostrailers.rss',
                    'http://www.archiveclassicmovies.com/democracy.xml',
                    'http://www.sesameworkshop.org/podcasts/sesamestreet/rss.xml',
                    'http://www.hbo.com/apps/podcasts/podcast.xml?a=intreatment'),
            ],
            [
                ('Music', 'music.png',
                    'http://www.telemusicvision.com/videos/rss.php?i=1',
                    'http://revision3.com/notmtv/feed/quicktime-large',
                    'http://feeds.feedburner.com/theswitched',
                    'http://feeds.feedburner.com/volcast',
                    'http://abcnews.go.com/xmldata/xmlPodcast?id=1456635&src=i'),
                ('Tech', 'tech.png',
                    'http://feeds.feedburner.com/TEDTalks_video',
                    'http://revision3.com/tekzilla/feed/quicktime-high-definition',
                    'http://jetset.blip.tv/?skin=rss',
                    'http://www.podshow.com/feeds/gbtv.xml',
                    'http://revision3.com/diggnation/feed/quicktime-large',
                    'http://feeds.feedburner.com/webbalert')
            ],
            [
                ('Science', 'science.png',
                    'http://feeds.feedburner.com/Terravideos',
                    'http://www.pbs.org/wnet/nature/rss/podcast.xml',
                    'http://podcast.nationalgeographic.com/wild-chronicles/',
                    'http://krampf.blip.tv/rss',
                    'http://www.discovery.com/radio/xml/sciencevideo.xml',
                    'http://www.discovery.com/radio/xml/discovery_video.xml'),
                ('Entertainment', 'entertainment.png',
                    'http://feeds.boingboing.net/boingboing/tv',
                    'http://revision3.com/webdrifter/feed/quicktime-high-definition',
                    'http://feeds.theonion.com/OnionNewsNetwork',
                    'http://feeds.feedburner.com/AskANinja',
                    'http://www.channelfrederator.com/rss',
                    'http://feeds.feedburner.com/classicanimation',
                    'http://www.hbo.com/apps/podcasts/podcast.xml?a=intreatment')
            ],
            [
                ('News', 'news.png',
                    'http://feeds.cbsnews.com/podcast_eveningnews_video_1.rss',
                    'http://abcnews.go.com/xmldata/xmlPodcast?id=1478958&src=i',
                    'http://podcast.msnbc.com/audio/podcast/MSNBC-NN-NETCAST-M4V.xml',
                    'http://ewheel.democracynow.org/rss.xml',
                    'http://submedia.tv/submediatv/bm/rss/2',
                    'http://www.rocketboom.com/vlog/rb_hd.xml'
                ),
                ('Food', 'food.png',
                    'http://www.epicurious.com/services/rss/feeds/sitewide_podcast.xml',
                    'http://aww.ninemsn.com.au/podcast/freshtv/video/',
                    'http://www.simplyming.org/rss/vodcast.xml',
                    'http://www.foodguru.com/podcast/xml.xml',
                    'http://feeds.feedburner.com/averagebetty_itunes_video')
            ]
        ]
    channel_columns = [[(column[0], column[1],
        util.get_subscription_url(*column[2:]))
        for column in row] for row in channel_packs]
    return util.render_to_response(request, 'firsttime.html',
            { 'channel_columns': channel_columns,
              'MOVIE_URL_FLASH': 'http://blip.tv/file/get/Miropcf-FundraisingUpdate155.flv',
              'MOVIE_URL_MP4': 'http://blip.tv/file/get/Miropcf-FundraisingUpdate155.mp4',
              })
