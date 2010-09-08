# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.views.decorators.cache import cache_control

from channelguide.guide.views import frontpage

@cache_control(max_age=3600)
def index(request):
    return frontpage.index(request, show_welcome=True)
