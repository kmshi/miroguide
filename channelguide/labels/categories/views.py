# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.utils.translation import gettext as _
from django.contrib.auth.decorators import permission_required
from django.db.models import Count
from django.template.context import RequestContext
from django.shortcuts import render_to_response

from channelguide import util
from channelguide.labels.models import Category
from channelguide.channels.models import Channel

def index(request):
    audio = request.path.startswith('/audio')
    categories = Category.objects.order_by('name')
    for category in categories:
        if audio:
            channels = category.get_list_channels(show_state=Channel.AUDIO)
        else:
            channels = category.get_list_channels(show_state=Channel.APPROVED)
        category.popular_channels = channels
    return render_to_response('labels/genres-list.html', {
            'group_name': _('Genres'),
            'categories': categories,
            'audio': audio
            }, context_instance=RequestContext(request))

@permission_required('labels.change_category')
def toggle_frontpage(request):
    if request.method == 'POST':
        category = Category.objects.get(pk=request.POST['id'])
        category.on_frontpage = not category.on_frontpage
        category.save()
    return util.redirect('genres/moderate')
