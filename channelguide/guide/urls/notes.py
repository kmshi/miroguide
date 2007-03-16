from django.conf.urls.defaults import *

urlpatterns = patterns('channelguide.guide.views.notes',
    (r'^new$', 'add_note'),
    (r'^(\d+)$', 'note'),
    (r'^moderator-board$', 'moderator_board'),
    (r'^new-moderator-post$', 'add_moderator_post'),
    (r'^post-(\d+)$', 'post'),
)
