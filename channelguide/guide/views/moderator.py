# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.http import HttpResponseRedirect
from django.core.paginator import Paginator, InvalidPage
from django.utils.translation import gettext as _

from channelguide import util, cache
from channelguide.guide import templateutil
from channelguide.guide.auth import moderator_required, supermoderator_required
from channelguide.guide.models import (Channel, ModeratorPost, FeaturedQueue,
                                       Flag)

from datetime import date, timedelta

def count_for_state(connection, state):
    return Channel.query(state=state).count(connection)

@moderator_required
def index(request):
    context = {}

    query = Channel.query(Channel.c.moderator_shared_at.is_not(None))
    query.order_by('moderator_shared_at', desc=True).limit(5)
    context['shared_channels'] = query.execute(request.connection)
    for channel in context['shared_channels']:
        channel.update_moderator_shared_by(request.connection)

    context['new_count'] = count_for_state(request.connection, Channel.NEW)
    context['dont_know_count'] = count_for_state(request.connection,
            Channel.DONT_KNOW)
    waiting_q = Channel.query(Channel.c.waiting_for_reply_date.is_not(None))
    context['waiting_count'] = waiting_q.count(request.connection)
    context['suspended_count'] = count_for_state(request.connection,
            Channel.SUSPENDED)
    context['rejected_count'] = count_for_state(request.connection,
            Channel.REJECTED)
    hd_flagged_query = Flag.query(flag=Flag.NOT_HD).join('channel')
    hd_flagged_query.where(hd_flagged_query.joins['channel'].c.hi_def == True)
    hd_flagged_query.group_by(Flag.c.channel_id)
    context['hd_flagged_count'] = len(hd_flagged_query.execute(request.connection))
    context['featured_count'] = FeaturedQueue.query(FeaturedQueue.c.state==0).count(request.connection)

    query = ModeratorPost.query().order_by('created_at', desc=True)
    query.join('user')
    context['latest_posts'] = query.limit(5).execute(request.connection)
    context['post_count'] = ModeratorPost.query().count(request.connection)

    return util.render_to_response(request, 'moderate.html', context)

@moderator_required
def channel_list(request, state):
    query = Channel.query().join('owner').order_by('creation_time')
    if state == 'waiting':
        query.where(Channel.c.waiting_for_reply_date.is_not(None))
        query.order_by('waiting_for_reply_date')
        header = _("Channels Waiting For Replies")
    elif state == 'dont-know':
        query.where(state=Channel.DONT_KNOW)
        header = _("Channels Flagged Don't Know By a Moderator")
    elif state == 'rejected':
        query.where(state=Channel.REJECTED)
        header = _("Rejected Channels")
    elif state == 'suspended':
        query.where(state=Channel.SUSPENDED)
        header = _("Suspended Channels")
    elif state == 'featured':
        query.join('featured_queue')
        query.where(query.joins['featured_queue'].c.state == FeaturedQueue.IN_QUEUE)
        header = _("Featured Queue")
    elif state == 'hd-flagged':
        query = Channel.query().join('owner')
        query.join('flags')
        query.load('flag_count')
        query.order_by('flag_count', desc=True)
        query.where(hi_def=True)
        query.where(query.joins['flags'].c.flag == Flag.NOT_HD)
        header = _('Flagged HD Channels')
    else:
        query.where(state=Channel.NEW)
        header = _("Unreviewed Channels")

    paginator = Paginator(templateutil.QueryObjectList(request.connection,
                                                       query), 20)
    try:
        page = paginator.page(request.GET.get('page', 1))
    except InvalidPage:
        return HttpResponseRedirect(request.path)

    return util.render_to_response(request, 'moderator-channel-list.html', {
            'request': request,
            'page': page,
            'header': header,
            'subscribe_all_link': util.make_link(
                util.get_subscription_url(*[channel.url for channel in
                                            page.object_list
                                            if channel.url is not None]),
                _("Subscribe to all %i channels on this page") % len(
                    page.object_list))
            })

@moderator_required
def shared(request):
    query = Channel.query(Channel.c.moderator_shared_at.is_not(None))
    query.order_by('moderator_shared_at', desc=True)
    paginator = Paginator(templateutil.QueryObjectList(request.connection,
                                                       query), 10)
    page = paginator.page(request.GET.get('page', 1))
    for channel in page.object_list:
        channel.update_moderator_shared_by(request.connection)

    return util.render_to_response(request, "shared.html", {
        'page': page
        })

@moderator_required
def how_to_moderate(request):
    return util.render_to_response(request, 'how-to-moderate.html')


@supermoderator_required
def stats(request):
    todays = [int(request.connection.execute('SELECT SUM(subscription_count_today) FROM cg_channel_generated_stats')[0][0])]
    months = [int(request.connection.execute('SELECT SUM(subscription_count_month) FROM cg_channel_generated_stats')[0][0])]

    for i in range(1, 100):
        key = 'stats:day:%i:%i:%i' % (date.today() - timedelta(days=i)).timetuple()[:3]
        val = cache.client.get(key)
        if val is None:
            val = request.connection.execute('SELECT COUNT(*) FROM cg_channel_subscription WHERE timestamp > DATE_SUB(NOW(), INTERVAL %s DAY) AND timestamp < DATE_SUB(NOW(), INTERVAL %s DAY)', (i+1, i))[0][0]
            cache.client.set(key, val)
        todays.append(val)

    for i in range(1, 12):
        key = 'stats:month:%i:%i' % (date.today() - timedelta(days=31*i)).timetuple()[:2]
        val = cache.client.get(key)
        if val is None:
            val = request.connection.execute('SELECT COUNT(*) FROM cg_channel_subscription WHERE timestamp > DATE_SUB(NOW(), INTERVAL %s MONTH) AND timestamp < DATE_SUB(NOW(), INTERVAL %s MONTH)', (i+1, i))[0][0]
            cache.client.set(key, val)
        months.append(val)

    return util.render_to_response(request, 'stats.html', {
            'todays': todays,
            'min_today': min(todays),
            'max_today': max(todays),
            'months': months,
            'min_month': min(months),
            'max_month': max(months)})

