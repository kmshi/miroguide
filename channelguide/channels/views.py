# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

import urlparse

from django.conf import settings
from django.utils.decorators import decorator_from_middleware
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.views import redirect_to_login
from django.http import Http404, HttpResponse
from django.template.context import RequestContext
from django.utils.translation import gettext as _
from django.core.paginator import Paginator, InvalidPage
from django.shortcuts import render_to_response, get_object_or_404

from channelguide import util
from channelguide.cache.decorators import cache_with_sites
from channelguide.cache.middleware import UserCacheMiddleware
from channelguide.guide.auth import admin_required
from channelguide.guide.country import country_code
from channelguide.api import utils as api_utils
from channelguide.channels.models import Channel, Item, AddedChannel
from channelguide.channels import forms
from channelguide.flags.models import Flag
from channelguide.ratings.models import GeneratedRatings
from channelguide.notes.models import ChannelNote
from channelguide.featured.models import FeaturedQueue
from channelguide.featured.forms import FeaturedEmailForm
from channelguide.notes.utils import get_note_info, make_rejection_note

class ApiObjectList:
    def __init__(self, request, filter, value, sort, loads, country_code=None):
        self.request = request
        self.filter = filter
        self.value = value
        self.sort = sort
        self.loads = loads
        self.country_code = country_code
        if 'rating' in sort:
            self.count_sort = 'ratingcount'
        else:
            self.count_sort = 'count'

    def call(self, *args, **kw):
        """
        Call the appropriate API function.  We do it this way because assigning
        a function as an attribute of a class makes it a method, and we don't
        want the extra `self` argument.
        """
        raise NotImplementedError()

    def count_all(self):
        """
        Return the count of items, not filtering by country.
        """
        return int(self.call(self.request, self.filter,
                             self.value, self.count_sort))

    def __len__(self):
        return int(self.call(self.request, self.filter,
                             self.value, self.count_sort,
                             country_code = self.country_code))

    def __getslice__(self, offset, end):
        limit = end - offset
        return tuple(self.call(self.request, self.filter, self.value,
                               self.sort, limit, offset, self.loads,
                               self.country_code))

class FeedObjectList(ApiObjectList):
    def call(self, *args, **kw):
        return api_utils.get_feeds(*args, **kw)

class SiteObjectList(ApiObjectList):
    def call(self, *args, **kw):
        return api_utils.get_sites(*args, **kw)

class ChannelCacheMiddleware(UserCacheMiddleware):
    def get_cache_key_tuple(self, request):
        channelId = request.path.split('/')[-1].encode('utf8')
        self.namespace = ('channel', 'Channel:%s' % channelId)
        return UserCacheMiddleware.get_cache_key_tuple(self, request)


def channel(request, id):
    if request.method in ('GET', 'HEAD'):
        return show(request, id)
    else:
        channel = get_object_or_404(Channel, pk=id)
        action = request.POST.get('action')
        if action == 'toggle-moderator-share':
            if not request.user.has_perm('channels.change_channel'):
                return redirect_to_login(request.path)
            channel.toggle_moderator_share(request.user)
        elif action == 'toggle-hd':
            if not request.user.has_perm('channels.change_channel'):
                return redirect_to_login(request.path)
            channel.hi_def = not channel.hi_def
            if channel.hi_def:
                Flag.objects.filter(channel=channel,
                            flag=Flag.NOT_HD).delete()
        elif action == 'set-hd':
            value = request.POST.get('value', 'off').lower()
            if value == 'on':
                channel.hi_def = True
            else:
                channel.hi_def = False
            Flag.objects.filter(channel=channel,
                                flag=Flag.NOT_HD).delete()
        elif action == 'feature':
            if not request.user.has_perm('featured.add_featuredqueue'):
                return redirect_to_login(request.path)
            FeaturedQueue.objects.feature(channel, request.user)
            return util.redirect_to_referrer(request)
        elif action == 'unfeature':
            if not request.user.has_perm('featured.add_featuredqueue'):
                return redirect_to_login(request.path)
            if channel.featured_queue.state == FeaturedQueue.PAST:
                FeaturedQueue.objects.feature(channel, request.user)
            else:
                FeaturedQueue.objects.unfeature(channel)
            return util.redirect_to_referrer(request)
        elif action == 'change-state':
            if not request.user.has_perm('channels.change_channel'):
                return redirect_to_login(request.path)
            submit_value = request.POST['submit']
            if submit_value.startswith('Approve'):
                newstate = Channel.APPROVED
                if '&' in submit_value: # feature or share
                    if request.user.has_perm('featured.add_featuredqueue'):
                        FeaturedQueue.objects.feature(channel, request.user)
                    else:
                        channel.toggle_moderator_share(request.user)
            elif submit_value == "Don't Know":
                newstate = Channel.DONT_KNOW
            elif submit_value == 'Unapprove':
                newstate = Channel.NEW
            elif submit_value == 'Audio':
                newstate = Channel.AUDIO
            elif submit_value == 'Delete':
                if not request.user.is_superuser and \
                        request.user != channel.owner:
                    return redirect_to_login(request.path)
                newstate = Channel.REJECTED
            else:
                newstate = None
            if newstate is not None:
                channel.change_state(request.user, newstate)
        elif action == 'mark-replied':
            if not request.user.has_perm('channels.change_channel'):
                return redirect_to_login(request.path)
            channel.waiting_for_reply_date = None
            channel.save()
        elif action == 'standard-reject':
            if not request.user.has_perm('channels.change_channel'):
                return redirect_to_login(request.path)
            reason = request.POST['submit']
            note = make_rejection_note(channel, request.user, reason)
            note.save()
            note.send_email()
            channel.change_state(request.user, Channel.REJECTED)
        elif action == 'reject':
            if not request.user.has_perm('channels.change_channel'):
                return redirect_to_login(request.path)
            body = request.POST.get('body')
            if body:
                note = ChannelNote.create_note_from_request(request)
                note.channel = channel
                note.save()
                note.send_email(request.POST.get('email'))
                channel.change_state(request.user, Channel.REJECTED)
            else:
                msg = _("Rejection emails need a body")
                request.session['channel-edit-error'] = msg
        elif action == 'email':
            if not request.user.has_perm('featured.add_featuredqueue'):
                return redirect_to_login(request.path)
            _type = request.POST['type']
            title = _('%s featured on Miro Guide') % channel.name
            body = request.POST['body']
            email = request.POST['email']
            form = FeaturedEmailForm(request, channel,
                                     {'email': email,
                                      'title': title,
                                      'body': body})
            form.full_clean()
            form.send_email()
            if _type == 'Approve & Feature':
                channel.change_state(request.user, Channel.APPROVED)
            FeaturedQueue.objects.feature(channel, request.user)
        elif action == "change-owner":
            if not request.user.has_perm('channels.change_owner'):
                return redirect_to_login(request.path)
            new_owner = request.POST['owner']
            user = User.objects.get(username=new_owner)
            if channel.owner != user:
                tags = channel.get_tags_for_owner()
                for tag in tags:
                    tag.delete()
                channel.owner = user
                channel.add_tags(user, [tag.name for tag in tags])
        else:
            raise Http404
        channel.save()
    return util.redirect_to_referrer(request)


@decorator_from_middleware(ChannelCacheMiddleware)
def show(request, id, featured_form=None):
    c = get_object_or_404(Channel, pk=id)
    try:
        c.rating
    except GeneratedRatings.DoesNotExist:
        c.rating = GeneratedRatings.objects.create(channel=c)
    # redirect old URLs to canonical ones
    if request.path != c.get_url():
        return util.redirect(c.get_absolute_url(), request.GET)

    item_paginator = Paginator(c.items.all(), 10)
    try:
        item_page = item_paginator.page(request.GET.get('page', 1))
    except InvalidPage:
        raise Http404

    is_miro = bool(util.get_miro_version(request.META.get('HTTP_USER_AGENT')))

    share_links = share_url = None
    if request.GET.get('share') == 'true':
        share_url = urlparse.urljoin(
            settings.BASE_URL_FULL,
            '/feeds/%s' % id)
        share_links = util.get_share_links(share_url, c.name)

    country = country_code(request)
    context = {
        'channel': c,
        'item_page': item_page,
        'is_miro': is_miro,
        'show_edit_button': c.can_edit(request.user),
        'show_extra_info': c.can_edit(request.user),
        'link_to_channel': True,
        'BASE_URL': settings.BASE_URL,
        'feed_url': c.url,
        'share_url': share_url,
        'share_type': 'feed',
        'share_links': share_links,
        'country': country,
        'audio': c.state == c.AUDIO}

    if share_url:
        context['google_analytics_ua'] = None

    if country and c.geoip and country not in c.geoip.split(','):
        # restricted channel
        request.add_notification(None, _('This show may not be available to you, '
                                   'as it is restricted to certain countries.'))

    if request.user.has_perm('featured.change_featuredqueue'):
        try:
            featured_queue = c.featured_queue
        except FeaturedQueue.DoesNotExist:
            pass
        else:
            if featured_queue.state in (
                FeaturedQueue.IN_QUEUE, FeaturedQueue.CURRENT):
                c.featured = True
            if c.featured_emails.count():
                last_featured_email = c.featured_emails.all()[0]
            else:
                last_featured_email = None
            if featured_form is None:
                featured_form = FeaturedEmailForm(request, c)
            context['featured_email_form'] = featured_form
            context['last_featured_email'] = last_featured_email
    return render_to_response('channels/show-channel.html', context,
                              context_instance=RequestContext(request))

@login_required
def user_subscriptions(request):
    feed_paginator = Paginator(Channel.objects.filter(
            url__isnull=False,
            added_channels__user=request.user), 50)
    try:
        feed_page = feed_paginator.page(request.GET.get('page', 1))
    except InvalidPage:
        raise Http404

    site_paginator = Paginator(Channel.objects.filter(
            url__isnull=True,
            added_channels__user=request.user), 50)
    try:
        site_page = site_paginator.page(request.GET.get('page', 1))
    except InvalidPage:
        raise Http404

    if site_paginator.count > feed_paginator.count:
        biggest = site_page
    else:
        biggest = feed_page

    return render_to_response('channels/listing.html', {
            'title': _('Subscriptions for %s') % request.user,
            'sort': 'name',
            'current_page': biggest.number,
            'feed_page': feed_page,
            'site_page': site_page,
            'biggest': biggest,
            'geoip_filtered': False,
            'miro_version_pre_sites': False,
            'miro_on_linux': False,
        }, context_instance=RequestContext(request))

def user_add(request, id):
    if request.user.is_authenticated():
        channel = get_object_or_404(Channel, pk=int(id))
        AddedChannel.objects.get_or_create(channel=channel,
                                           user=request.user)
    return HttpResponse("Added!")

@cache_with_sites('namespace')
def filtered_listing(request, value=None, filter=None, limit=10,
                     title='Filtered Listing', default_sort=None):
    if not filter:
        raise Http404
    page = request.GET.get('page', 1)
    try:
        page = int(page)
    except ValueError:
        raise Http404
    sort = request.GET.get('sort', default_sort)
    if default_sort is None and sort is None:
        sort = '-popular'
    geoip = request.GET.get('geoip', None)
    if geoip != 'off':
        geoip = country_code(request)
    else:
        geoip = None
    if isinstance(filter, basestring):
        filter = [filter]
        value = [value]
    if 'audio' not in filter:
        filter.append('audio')
        if request.path.startswith('/audio'):
            value.append(True)
        else:
            value.append(False)
    feed_object_list = FeedObjectList(request,
                                      filter, value, sort,
                                      ('stats', 'rating'), geoip)
    feed_paginator = Paginator(feed_object_list, limit)
    try:
        feed_page = feed_paginator.page(page)
    except InvalidPage:
        feed_page = None

    miro_version_pre_sites = miro_on_linux = False
    miro_version = util.get_miro_version(request.META.get('HTTP_USER_AGENT'))

    if miro_version:
        if int(miro_version.split('.')[0]) < 2:
            miro_version_pre_sites = True

    site_page = None
    site_paginator = None
    site_object_list = None
    # There are two cases where we don't generate a site object list:
    #  - If it's pre-miro 2.0 (doesn't support site object lists)
    #  - If it's Miro on Linux... because unfortunately most 'sites'
    #    are flash-based, and linux + flash == teh suck :\
    if not (miro_version_pre_sites
            or ('Miro' in request.META.get('HTTP_USER_AGENT', '')
                and 'X11' in request.META.get('HTTP_USER_AGENT', ''))):
        site_object_list = SiteObjectList(
            request, filter, value, sort,
            ('stats', 'rating'),
            geoip)
        site_paginator = Paginator(site_object_list, limit)

        try:
            site_page = site_paginator.page(page)
        except InvalidPage:
            site_page = None
    else:
        miro_on_linux = True

    # find the biggest paginator and use that page for calculating the links
    if not feed_paginator:
        biggest = site_page
    elif not site_paginator:
        biggest = feed_page
    elif feed_paginator.count > site_paginator.count:
        biggest = feed_page
    else:
        biggest = site_page

    if biggest is None:
        raise Http404
    
    geoip_filtered = False
    if geoip:
        if (feed_object_list.count_all() != feed_paginator.count
            or (site_object_list is not None
                and site_object_list.count_all() != site_paginator.count)):
            args = request.GET.copy()
            args['geoip'] = 'off'
            geoip_filtered = util.make_absolute_url(request.path, args)

    video_count = audio_count = None

    if value[filter.index('audio')]:
        video_filter = filter[:]
        video_values = value[:]
        index = video_filter.index('audio')
        video_values[index] = False
        video_count = len(FeedObjectList(request, video_filter, video_values,
                                         sort, geoip))
    else:
        audio_filter = filter[:]
        audio_values = value[:]
        index = audio_filter.index('audio')
        audio_values[index] = True
        audio_count = len(FeedObjectList(request, audio_filter, audio_values,
                                         sort, geoip))

    return render_to_response('channels/listing.html', {
            'title': title % {'value': value[0]},
            'sort': sort,
            'filter': filter,
            'current_page': page,
            'feed_page': feed_page,
            'site_page': site_page,
            'biggest': biggest,
            'geoip_filtered': geoip_filtered,
            'miro_version_pre_sites': miro_version_pre_sites,
            'miro_on_linux': miro_on_linux,
            'search': 'search' in filter,
            'audio': value[filter.index('audio')],
            'video_count': video_count,
            'audio_count': audio_count
            }, context_instance=RequestContext(request))

@login_required
def edit_channel(request, id):
    channel = get_object_or_404(Channel, pk=id)
    if not request.user.has_perm('channels.change_channel') and \
            channel.owner != request.user:
        return redirect_to_login(request.path)

    if request.method != 'POST':
        form = forms.EditChannelForm(channel)
    else:
        form = forms.EditChannelForm(channel, request.POST, request.FILES)
        if form.is_valid():
            form.update_channel(channel)
            if request.FILES.get('thumbnail_file'):
                request.FILES['thumbnail_file'].close()
            return util.redirect_to_referrer(request)
        else:
            form.save_submitted_thumbnail()
    context = form.get_template_data()
    context['channel'] = channel
    context['notes'] = get_note_info(channel, request.user)
    if form.set_image_from_channel:
        context['thumbnail_description'] = _("Current image (no change)")
    else:
        context['thumbnail_description'] = _("Current image (uploaded)")
    response = render_to_response('channels/edit-channel.html',
                                  context,
                                  context_instance=RequestContext(request))
    if request.FILES.get('thumbnail_file'):
        request.FILES['thumbnail_file'].close()
    return response

@permission_required('channels.change_channel')
def email(request, id):
    channel = get_object_or_404(Channel, pk=id)
    email_type = request.REQUEST['type']
    skipable = True
    if request.user.get_full_name():
        mod_name = '%s (%s)' % (request.user.get_full_name(), request.user.username)
    else:
        mod_name = request.user.username
    common_body = """%s is in line to be featured on the Miro Channel Guide, which is great because 50,000-100,000 people see this page every day!""" % channel.name
    common_middle = """Depending on the number of channels in line, %s should appear on the front page in the next few days; it will remain in the spotlight for 4 full days at: https://miroguide.com/""" % channel.name
    common_footer ="""If you want to show off your featured channel, you can link to this page: https://www.miroguide.com/featured/

Regards,
%s

PS. Miro 1-click links rock! They give your viewers a simple way to go directly
from your website to being subscribed to your feed in Miro:
http://subscribe.getmiro.com/""" % mod_name

    if channel.owner.username != 'freelance':
        if channel.owner.get_full_name():
            name = channel.owner.get_full_name()
        else:
            name = channel.owner.username
        body  = """Hello %s,

%s

%s

Modify your channel and get stats here: %s#edit

%s""" % (name, common_body, common_middle, channel.get_absolute_url(),
        common_footer)
    else:
        body = """Hello,

%s  The Guide is part of Miro, the free internet TV application: http://www.getmiro.com/

%s

Currently we're managing your channel -- if you'd like to take control, view stggats, and be able to change the images and details associated with it, please contact us at: support@pculture.org

%s""" % (common_body, common_middle, common_footer)
    if email_type in ('Feature', 'Refeature'):
        action = 'feature'
    elif email_type == 'Approve & Feature':
        action = 'change-state'
    elif email_type == "Custom":
        email_type = 'Reject'
        action = 'reject'
        body = ''
        skipable = False
    else:
        raise Http404
    if action != 'reject' and channel.owner.email != 'Dean@NottheMessiah.net':
        email = channel.owner.email
    else:
        email = ''
    return util.render_to_response(request, 'email-form.html',
                                   {'channel': channel,
                                    'type': email_type,
                                    'action': action,
                                    'body': body,
                                    'email': email,
                                    'skipable': skipable})

@admin_required
def email_owners(request):
    if request.method != 'POST':
        form = forms.EmailChannelOwnersForm()
    else:
        form = forms.EmailChannelOwnersForm(request.POST)
        if form.is_valid():
            form.send_email(request.user)
            return util.redirect('moderate')
    return util.render_to_response(request, 'email-channel-owners.html', {
        'form': form})

def latest(request, id):
    items = Item.objects.filter(channel=id).order_by('-date')
    if not items:
        raise Http404
    else:
        return util.redirect(items[0].url)

def item(request, id):
    item = get_object_or_404(Item, pk=id)
    return util.render_to_response(request, 'playback.html',
                                   {'item': item})
