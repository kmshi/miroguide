# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from channelguide import cache
from channelguide.guide.views import frontpage

@cache.aggresively_cache
@cache.cache_page_externally_for(3600)
def index(request):
    return frontpage.index(request, show_welcome=True)
