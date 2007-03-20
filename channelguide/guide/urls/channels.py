from django.conf.urls.defaults import *

urlpatterns = patterns('channelguide.guide.views.channels',
    (r'^submitted_thumbnails/(\d+)$', 'submitted_thumbnail'),
    (r'^(\d+)$', 'channel'),
    (r'^popular$', 'popular'),
    (r'^by-name$', 'by_name'),
    (r'^features$', 'features'),
    (r'^recent$', 'recent'),
    (r'^moderate$', 'moderate'),
    (r'^unapproved/([\w-]+)$', 'unapproved_channels'),
    (r'^subscribe/(\d+)$', 'subscribe'),
    (r'^submit$', 'submit_feed'),
    (r'^submit/step1$', 'submit_feed'),
    (r'^submit/step2$', 'submit_channel'),
    (r'^submit/after$', 'after_submit'),
    (r'^user/(\d+)$', 'for_user'),
)
