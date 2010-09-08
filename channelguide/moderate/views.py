# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.http import HttpResponseRedirect
from django.core import cache
from django.core.paginator import Paginator, InvalidPage
from django.contrib.auth.decorators import permission_required
from django.db.models import Count
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.translation import gettext as _

from channelguide import util
from channelguide.guide.auth import admin_required
from channelguide.moderate.models import ModeratorAction
from channelguide.channels.models import Channel
from channelguide.flags.models import Flag
from channelguide.notes.models import ModeratorPost
from channelguide.featured.models import FeaturedQueue

from datetime import date, timedelta

def count_for_state(state):
    return Channel.objects.filter(state=state).count()

@permission_required('moderate.add_moderatoraction')
def index(request):
    context = {}

    context['shared_channels'] = Channel.objects.filter(
        moderator_shared_at__isnull=False).order_by('-moderator_shared_at')[:5]

    context['new_count'] = count_for_state(Channel.NEW)
    context['dont_know_count'] = count_for_state(Channel.DONT_KNOW)
    context['waiting_count'] = Channel.objects.filter(
        waiting_for_reply_date__isnull=False).count()
    context['suspended_count'] = count_for_state(Channel.SUSPENDED)
    context['rejected_count'] = count_for_state(Channel.REJECTED)
    hd_flagged_query = Flag.objects.filter(
        flag=Flag.NOT_HD,
        channel__hi_def=True).values('channel').order_by().distinct()
    context['hd_flagged_count'] = hd_flagged_query.count()
    context['featured_count'] = FeaturedQueue.objects.filter(state=0).count()

    query = ModeratorPost.objects.order_by('-created_at')
    context['post_count'] = query.count()
    context['latest_posts'] = query[:5]

    return render_to_response('moderate/moderate.html',
                              context,
                              context_instance=RequestContext(request))

@permission_required('moderate.add_moderatoraction')
def channel_list(request, state):
    query = Channel.objects.extra(
        select={
            'owned_by_freelance':
                'owner_id='
            '(SELECT id FROM auth_user WHERE username="freelance")'
            })
    ordering = ['owned_by_freelance', 'creation_time']

    if state == 'waiting':
        query = query.filter(waiting_for_reply_date__isnull=False)
        ordering[1] = 'waiting_for_reply_date'
        header = _("Channels Waiting For Replies")
    elif state == 'dont-know':
        query = query.filter(state=Channel.DONT_KNOW)
        header = _("Channels Flagged Don't Know By a Moderator")
    elif state == 'rejected':
        query = query.filter(state=Channel.REJECTED)
        header = _("Rejected Channels")
    elif state == 'suspended':
        query = query.filter(state=Channel.SUSPENDED)
        header = _("Suspended Channels")
    elif state == 'featured':
        query = query.filter(featured_queue__state=FeaturedQueue.IN_QUEUE)
        header = _("Featured Queue")
    elif state == 'hd-flagged':
        query = Channel.objects.filter(hi_def=True).annotate(Count('flags'))
        query = query.order_by('-flags__count')
        ordering = None
        header = _('Flagged HD Channels')
    else:
        query = query.filter(state=Channel.NEW)
        header = _("Unreviewed Channels")

    if ordering:
        query = query.order_by(*ordering)
    paginator = Paginator(query, 20)
    try:
        page = paginator.page(request.GET.get('page', 1))
    except InvalidPage:
        return HttpResponseRedirect(request.path)

    return render_to_response('moderate/moderator-channel-list.html', {
            'request': request,
            'page': page,
            'header': header,
            'subscribe_all_link': util.make_link(
                util.get_subscription_url(*[channel.url for channel in
                                            page.object_list
                                            if channel.url is not None]),
                _("Subscribe to all %i channels on this page") % len(
                    page.object_list))
            }, context_instance=RequestContext(request))

@permission_required('moderate.add_moderatoraction')
def shared(request):
    query = Channel.objects.filter(moderator_shared_at__isnull=False).order_by(
        '-moderator_shared_at')
    paginator = Paginator(query, 10)
    page = paginator.page(request.GET.get('page', 1))

    return render_to_response("moderate/shared.html", {
        'page': page
        }, context_instance=RequestContext(request))


@admin_required
def history(request):
    paginator = Paginator(ModeratorAction.objects.all(), 30)
    page = paginator.page(request.GET.get('page', 1))
    return render_to_response('moderate/moderator-history.html', {
        'page': page,
        }, context_instance=RequestContext(request))

@permission_required('moderate.add_moderatoraction')
def how_to_moderate(request):
    return render_to_response('moderate/how-to-moderate.html',
                              context_instance=RequestContext(request))


@permission_required('subscriptions.create_generatedstats')
def stats(request):
    todays = [int(request.connection.execute('SELECT SUM(subscription_count_today) FROM cg_channel_generated_stats')[0][0])]
    today_keys = [('last_24 hours', todays[0])]
    months = [int(request.connection.execute('SELECT SUM(subscription_count_month) FROM cg_channel_generated_stats')[0][0])]
    month_keys = [('last_31_days', months[0])]

    for i in range(1, 100):
        tt = (date.today() - timedelta(days=i)).timetuple()[:3]
        key = 'stats:day:%i:%i:%i' % tt
        val = cache.cache.get(key)
        if val is None:
            val = request.connection.execute('SELECT COUNT(*) FROM cg_channel_subscription WHERE YEAR(timestamp) = %s AND MONTH(timestamp) = %s AND DAY(timestamp) = %s', tt)[0][0]
            cache.cache.set(key, val)
        today_keys.append((key, val))
        todays.append(val)

    for i in range(1, 12):
        tt = (date.today() - timedelta(days=30*i)).timetuple()[:2]
        key = 'stats:month:%i:%i' % tt
        val = cache.cache.get(key)
        if val is None:
            val = request.connection.execute('SELECT COUNT(*) FROM cg_channel_subscription WHERE YEAR(timestamp) = %s AND MONTH(timestamp) = %s', tt)[0][0]
            cache.cache.set(key, val)
        month_keys.append((key, val))
        months.append(val)

    return render_to_response('moderate/stats.html', {
            'today_keys': today_keys,
            'todays': reversed(todays),
            'min_today': min(todays),
            'max_today': max(todays),
            'month_keys': month_keys,
            'months': reversed(months),
            'min_month': min(months),
            'max_month': max(months)},
                              context_instance=RequestContext(request))
