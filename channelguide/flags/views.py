# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.http import Http404, HttpResponseRedirect
from django.utils.translation import gettext as _
from django.shortcuts import get_object_or_404

from channelguide.channels.models import Channel
from channelguide.flags.models import Flag

def flag(request, id):
    if 'flag' not in request.REQUEST:
        raise Http404
    try:
        flag = int(request.REQUEST['flag'])
    except ValueError:
        raise Http404
    request.add_notification(
        _('Thanks!'),
        _('Your flag has been recorded and will be reviewed by a moderator.'))
    channel = get_object_or_404(Channel, pk=id)
    if request.user.is_authenticated():
        user = request.user
    else:
        user = None
    existing_flags = Flag.objects.filter(channel=channel, user=user,
                                         flag=flag)
    if existing_flags.count():
        if existing_flags.count() > 1:
            # previous database had duplicate values
            for flag in existing_flags[1:]:
                flag.delete()
    else:
        Flag.objects.create(channel=channel, user=user,
                            flag=flag)
    return HttpResponseRedirect(channel.get_url())
