# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

import urlparse
import re, time

from django.conf import settings
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.template import loader
from django.utils.decorators import decorator_from_middleware
from django.utils.translation import gettext as _
from django.core.paginator import Paginator, InvalidPage

from channelguide import util, cache
from channelguide.cache import client
from channelguide.cache.middleware import UserCacheMiddleware
from channelguide.guide import api, forms, templateutil
from channelguide.guide.auth import (admin_required, moderator_required,
                                     login_required)
from channelguide.guide.country import country_code
from channelguide.guide.exceptions import AuthError
from channelguide.guide.models import (Channel, Item, User, FeaturedEmail,
                                       ModeratorAction, ChannelNote, Rating,
                                       FeaturedQueue, GeneratedRatings,
                                       Cobranding, AddedChannel)
from channelguide.guide.notes import get_note_info, make_rejection_note
from channelguide.guide.emailmessages import EmailMessage
from sqlhelper.sql.statement import Select
from sqlhelper import signals, exceptions


class ItemObjectList(templateutil.QueryObjectList):
    def __init__(self, connection, channel):
        self.connection = connection
        self.query = Item.query(Item.c.channel_id == channel.id).order_by(
            Item.c.date, desc=True).join('channel')

    def __len__(self):
        return int(self.query.count(
                self.connection))

    def __getslice__(self, offset, end):
        limit = end - offset
        return tuple(self.query.limit(limit).offset(offset).execute(
            self.connection))

class ApiObjectList:
    def __init__(self, request, filter, value, sort, loads, country_code):
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
        return api.get_feeds(*args, **kw)

class SiteObjectList(ApiObjectList):
    def call(self, *args, **kw):
        return api.get_sites(*args, **kw)

def _calculate_pages(request, page, default_page=1):
    page_range = page.paginator.page_range
    if page.paginator.num_pages > 9:
        low = page.number - 5
        high = page.number + 4
        if low < 0:
            high -= low
            low = 0
        if high > page.paginator.num_pages and low > 0:
            low += (page.paginator.num_pages - high)
            if low < 0:
                low = 0
        middle = page_range[low:high]
        if middle[:2] != [1, 2]:
            middle = [1, 2, None] + middle[3:]
        if middle[-2:] != [page.paginator.num_pages - 1, page.paginator.num_pages]:
            middle = middle[:-3] + [None, page.paginator.num_pages - 1,
                                    page.paginator.num_pages]
    else:
        middle = page_range
    path = request.path
    get_data = dict(request.GET)
    for number in middle:
        if number is not None:
            if number != default_page:
                get_data['page'] = str(number)
            else:
                try:
                    del get_data['page']
                except KeyError:
                    pass
            yield (number, util.make_absolute_url(path, get_data))
        else:
            yield ('tag', None)

class ChannelCacheMiddleware(UserCacheMiddleware):
    def get_cache_key_tuple(self, request):
        channelId = request.path.split('/')[-1].encode('utf8')
        self.namespace = ('channel', 'Channel:%s' % channelId)
        return UserCacheMiddleware.get_cache_key_tuple(self, request)


@moderator_required
def moderator_channel_list(request, state):
    query = Channel.query().join('owner')
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
        query.order_by(query.joins['featured_queue'].c.featured_at)
        header = _("Featured Queue")
    else:
        query.where(state=Channel.NEW)
        header = _("Unreviewed Channels")
    query.order_by('creation_time', query.joins['owner'].c.username != 'freelance')
    pager =  templateutil.Pager(10, query, request)

    return util.render_to_response(request, 'moderator-channel-list.html', {
        'pager': pager,
        'channels': pager.items,
        'header': header,
        'subscribe_all_link': util.make_link(
                util.get_subscription_url(*[channel.url for channel in
                                            pager.items]),
                _("Subscribe to all %i channels") % len(pager.items))
        })


def channel(request, id):
    if request.method == 'GET':
        return show(request, id)
    else:
        channel = util.get_object_or_404(request.connection, Channel, id)
        action = request.POST.get('action')
        if action == 'toggle-moderator-share':
            request.user.check_is_moderator()
            channel.toggle_moderator_share(request.user)
        elif action == 'toggle-hd':
            request.user.check_is_moderator()
            channel.hi_def = not channel.hi_def
        elif action == 'feature':
            request.user.check_is_supermoderator()
            FeaturedQueue.feature_channel(channel, request.user,
                    request.connection)
        elif action == 'unfeature':
            request.user.check_is_supermoderator()
            channel.join('featured_queue').execute(request.connection)
            if channel.featured_queue.state == FeaturedQueue.PAST:
                FeaturedQueue.feature_channel(channel, request.user,
                                              request.connection)
            else:
                FeaturedQueue.unfeature_channel(channel, request.connection)
        elif action == 'change-state':
            request.user.check_is_moderator()
            submit_value = request.POST['submit']
            if submit_value.startswith('Approve'):
                channel.join('owner').execute(request.connection)
                newstate = Channel.APPROVED
                if '&' in submit_value: # feature or share
                    if request.user.is_supermoderator():
                        FeaturedQueue.feature_channel(channel, request.user,
                                request.connection)
                    else:
                        channel.toggle_moderator_share(request.user)
            elif submit_value == "Don't Know":
                newstate = Channel.DONT_KNOW
            elif submit_value == 'Unapprove':
                newstate = Channel.NEW
            elif submit_value == 'Audio':
                newstate = Channel.AUDIO
            elif submit_value == 'Delete':
                if not request.user.is_admin() and \
                        request.user.id != channel.owner_id:
                            request.user.check_is_admin()
                newstate = Channel.REJECTED
            else:
                newstate = None
            if newstate is not None:
                channel.change_state(request.user, newstate,
                        request.connection)
        elif action == 'mark-replied':
            request.user.check_is_moderator()
            channel.waiting_for_reply_date = None
            channel.save(request.connection)
        elif action == 'standard-reject':
            request.user.check_is_moderator()
            reason = request.POST['submit']
            note = make_rejection_note(channel, request.user, reason)
            note.save(request.connection)
            note.send_email(request.connection)
            channel.change_state(request.user, Channel.REJECTED,
                    request.connection)
        elif action == 'reject':
            request.user.check_is_moderator()
            body = request.POST.get('body')
            if body:
                note = ChannelNote(request.user, body)
                note.channel = channel
                note.save(request.connection)
                note.send_email(request.connection, request.POST.get('email'))
                channel.change_state(request.user, Channel.REJECTED,
                        request.connection)
            else:
                msg = _("Rejection emails need a body")
                request.session['channel-edit-error'] = msg
        elif action == 'email':
            request.user.check_is_supermoderator()
            _type = request.POST['type']
            title = _('%s featured on Miro Guide') % channel.name
            body = request.POST['body']
            email = request.POST['email']
            message = EmailMessage(title, body)
            message.send_email([email])
            if _type == 'Approve & Feature':
                channel.change_state(request.user, Channel.APPROVED,
                        request.connection)
            FeaturedQueue.feature_channel(channel, request.user,
                    request.connection)
            obj = FeaturedEmail()
            obj.title = title
            obj.body = body
            obj.email = email
            obj.channel_id = id
            obj.sender_id = request.user.id
            obj.save(request.connection)
        elif action == "change-owner":
            request.user.check_is_supermoderator()
            new_owner = request.POST['owner']
            user = User.query(username=new_owner).get(request.connection)
            if channel.owner_id != user.id:
                tags = channel.get_tags_for_owner(request.connection)
                for tag in tags:
                    channel.delete_tag(request.connection, channel.owner, tag)
                channel.owner_id = user.id
                channel.add_tags(request.connection, user, [tag.name for tag in tags])
        channel.save(request.connection)
    return util.redirect_to_referrer(request)

@signals.record_update.connect
def on_channel_record_update(record):
    if isinstance(record, Channel):
        client.set('Channel:%s' % record.id, time.time())
    elif isinstance(record, Rating):
        client.set('Channel:%s' % record.channel_id, time.time())

@signals.record_insert.connect
def on_channel_record_insert(record):
    if isinstance(record, Rating):
        client.set('Channel:%s' % record.channel_id, time.time())

@decorator_from_middleware(ChannelCacheMiddleware)
def show(request, id, featured_form=None):
    query = Channel.query()
    query.join('categories', 'tags', 'rating', 'last_moderated_by')
    if request.user.is_supermoderator():
        query.join('featured_queue', 'featured_queue.featured_by')
    c = util.get_object_or_404(request.connection, query, id)
    # redirect old URLs to canonical ones
    if request.path != c.get_url():
        return util.redirect(c.get_absolute_url(), request.GET)
    if c.rating is None:
        c.rating = GeneratedRatings()
        c.rating.channel_id = c.id
        c.rating.save(request.connection)

    item_paginator = Paginator(ItemObjectList(request.connection, c), 10)
    item_page = item_paginator.page(request.GET.get('page', 1))

    is_miro = bool(util.get_miro_version(request.META['HTTP_USER_AGENT']))

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
        'item_page_links': _calculate_pages(request, item_page),
        'recommendations': get_recommendations(request, c),
        'show_edit_button': request.user.can_edit_channel(c),
        'show_extra_info': request.user.can_edit_channel(c),
        'link_to_channel': True,
        'BASE_URL': settings.BASE_URL,
        'rating_bar': get_show_rating_bar(request, c),
        'feed_url': c.url,
        'share_url': share_url,
        'share_type': 'feed',
        'share_links': share_links,
        'country': country,
        'geoip_restricted': (country and c.geoip and \
                             country not in c.geoip.split(','))}

    if share_url:
        context['google_analytics_ua'] = None

    if request.user.is_supermoderator():
        c.join('owner').execute(request.connection)
        if c.featured_queue and c.featured_queue.state in (
                FeaturedQueue.IN_QUEUE, FeaturedQueue.CURRENT):
            c.featured = True
        if c.featured and c.owner is not None:
            query = FeaturedEmail.query().join('sender')
            query.where(channel_id=c.id)
            query.order_by(FeaturedEmail.c.timestamp, desc=True)
            query.limit(1)
            last_featured_email = query.execute(request.connection)
            if last_featured_email:
                last_featured_email = last_featured_email[0]
            else:
                last_featured_email = None
            if featured_form is None:
                featured_form = forms.FeaturedEmailForm(request, c)
            context['featured_email_form'] = featured_form
            context['last_featured_email'] = last_featured_email
    return util.render_to_response(request, 'show-channel.html', context)

@login_required
def user_subscriptions(request):
    request.user.join('channel_subscriptions').execute(request.connection)
    request.user.channel_subscriptions.join('channel').execute(request.connection)
    return util.render_to_response(request, 'listing.html', {
        'results': (a.channel for a in request.user.channel_subscriptions),
        'count': len(request.user.channel_subscriptions),
        'title': _('Subscriptions for %s') % request.user.username,
        'header_class': 'rss',
        'intro': 'Intro',
        'page': 1,
        'next_page': None,
        'sort': None,
        })

def user_add(request, id):
    if request.user.is_authenticated():
        ac = AddedChannel(int(id), request.user.id)
        try:
            ac.save(request.connection)
        except exceptions.SQLError:
            pass
    return HttpResponse("Added!")


def subscribe_hit(request, id):
    """Used by our ajax call handleSubscriptionLink.  It will get a security
    error if we redirect it to a URL outside the channelguide, so we don't do
    that
    """
    ids = [id] + [int(k) for k in request.GET]
    for id in ids:
        channel = util.get_object_or_404(request.connection, Channel, id)
        referer = request.META.get('HTTP_REFERER', '')
        match = re.match(
            settings.BASE_URL_FULL + '(?(channels|feeds|shows)/(\d+)?',
            referer)
        if match and match.groups()[0] != id:
            ignore_for_recommendations = True
        elif referer == settings.BASE_URL_FULL + 'firsttime':
            ignore_for_recommendations = True
        else:
            ignore_for_recommendations = False
        ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        if ip == '127.0.0.1':
            ip = request.META.get('HTTP_X_FORWARDED_FOR', '0.0.0.0')
        try:
            channel.add_subscription(request.connection, ip,
                    ignore_for_recommendations=ignore_for_recommendations)
        except:
            pass # ignore errors silently
    return HttpResponse("Hit successfull")

def get_recommendations(request, channel):
    recSelect = Select('*')
    recSelect.froms.append('cg_channel_recommendations')
    recSelect.wheres.append('channel1_id=%s OR channel2_id=%s' % (
        channel.id, channel.id))
    recSelect.wheres.append('cosine>=0.025')
    recSelect.order_by.append('cosine DESC')
    elements = recSelect.execute(request.connection)
    recommendations = [e[0] == int(channel.id) and e[1] or e[0] for e in elements]
    categories1 = set(channel.categories)
    channels = []
    for rec in recommendations:
        if len(channels) == 3:
            break
        try:
            chan = Channel.query().join('categories',
                                        'rating').get(request.connection, rec)
        except LookupError:
            continue
        else:
            categories2 = set(chan.categories)
            if chan.state == Channel.APPROVED and not chan.archived and \
                   (channel.rating.average - chan.rating.average) <= 0.5 and \
                   bool(chan.url) == bool(channel.url):
                channels.append(chan)
    return channels

def rate(request, id):
    if not request.user.is_authenticated():
        if 'HTTP_REFERER' in request.META and not request.REQUEST.get('referer'):
            referer = request.META['HTTP_REFERER']
            if referer.startswith(settings.BASE_URL_FULL):
                referer = referer[len(settings.BASE_URL_FULL)-1:]
            request.META['QUERY_STRING'] += "%%26referer=%s" % referer
        raise AuthError("need to log in to rate")
    if request.REQUEST.get('rating', None) is None:
        try:
            dbRating = Rating.query(Rating.c.user_id==request.user.id,
                Rating.c.channel_id==id).get(request.connection)
            return HttpResponse('User Rating: %s' %  dbRating.rating)
        except Exception:
            raise Http404
    channel = util.get_object_or_404(request.connection,
            Channel.query().join('rating'), id)
    score = request.REQUEST.get('rating')
    if score not in ['0', '1', '2', '3', '4', '5']:
        raise Http404
    channel.rate(request.connection, request.user, score)
    if request.GET.get('referer'):
        redirect = request.GET['referer']
    else:
        redirect = channel.get_absolute_url()
    return HttpResponseRedirect(redirect)

@cache.aggresively_cache
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
    feed_object_list = FeedObjectList(request,
                                      filter, value, sort,
                                      ('subscription_count_month',
                                       'rating',
                                       'item_count'), geoip)
    feed_paginator = Paginator(feed_object_list, limit)
    try:
        feed_page = feed_paginator.page(page)
    except InvalidPage:
        feed_page = None

    miro_version_pre_sites = False
    miro_version = util.get_miro_version(request.META['HTTP_USER_AGENT'])

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
            or ('Miro' in request.META['HTTP_USER_AGENT']
                and 'X11' in request.META['HTTP_USER_AGENT'])):
        site_object_list = SiteObjectList(
            request, filter, value, sort,
            ('subscription_count_month', 'rating', 'item_count'),
            geoip)
        site_paginator = Paginator(site_object_list, limit)

        try:
            site_page = site_paginator.page(page)
        except InvalidPage:
            site_page = None

    # find the biggest paginator and use that page for calculating the links
    if not feed_paginator:
        biggest = site_page
    elif not site_paginator:
        biggest = feed_page
    elif feed_paginator.count > site_paginator.count:
        biggest = feed_page
    else:
        biggest = site_page

    geoip_filtered = False
    if geoip:
        if (feed_object_list.count_all() != feed_paginator.count
            or (site_object_list
                and site_object_list.count_all() != site_paginator.count)):
            args = request.GET.copy()
            args['geoip'] = 'off'
            geoip_filtered = util.make_absolute_url(request.path, args)
    return util.render_to_response(request, 'listing.html', {
        'title': title % {'value': value},
        'sort': sort,
        'current_page': page,
        'pages': _calculate_pages(request, biggest),
        'feed_page': feed_page,
        'site_page': site_page,
        'geoip_filtered': geoip_filtered,
        'miro_version_pre_sites': miro_version_pre_sites,
        })

def for_user(request, user_name_or_id):
    try:
        user = User.query(username=user_name_or_id).get(request.connection)
    except LookupError:
        user = util.get_object_or_404(request.connection, User,
                                      user_name_or_id)
    expected_path = '/user/%s' % user.username
    if request.path != expected_path:
        return util.redirect(expected_path)
    query = Channel.query(owner_id=user.id, user=request.user)
    query.join('owner', 'last_moderated_by', 'featured_queue', 'featured_queue.featured_by')
    query.order_by(Channel.c.name)
    if request.user.is_admin() or request.user.id == user.id:
        try:
            cobrand = Cobranding.get(request.connection, user.username)
        except:
            cobrand = None
    else:
        cobrand = None
    paginator = Paginator(templateutil.QueryObjectList(request.connection,
                                                       query), 10)
    page = paginator.page(request.GET.get('page', 1))
    return util.render_to_response(request, 'for-user.html', {
        'for_user': user,
        'cobrand': cobrand,
        'page': page,
        })

@login_required
def edit_channel(request, id):
    query = Channel.query()
    query.join('language', 'categories', 'notes', 'notes.user')
    query.load('subscription_count_today', 'subscription_count_today_rank')
    query.load('subscription_count_month', 'subscription_count_month_rank')
    query.load('subscription_count', 'subscription_count_rank')
    channel = util.get_object_or_404(request.connection, query, id)
    request.user.check_can_edit(channel)
    if request.method != 'POST':
        form = forms.EditChannelForm(request, channel)
    else:
        form = forms.EditChannelForm(request, channel,
                util.copy_post_and_files(request))
        if form.is_valid():
            form.update_channel(channel)
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
    return util.render_to_response(request, 'edit-channel.html', context)

@moderator_required
def email(request, id):
    channel = util.get_object_or_404(request.connection, Channel, id)
    channel.join('owner').execute(request.connection)
    email_type = request.REQUEST['type']
    skipable = True
    if request.user.has_full_name():
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
        if channel.owner.has_full_name():
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

Currently we're managing your channel -- if you'd like to take control, view stats, and be able to change the images and details associated with it, please contact us at: support@pculture.org

%s""" % (common_body, common_middle, common_footer)
    if email_type == 'Feature':
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
    return util.render_to_response(request, 'email-form.html',
            {'channel': channel, 'type': email_type,
                'action': action, 'body': body, 'skipable': skipable})

@admin_required
def moderator_history(request):
    query = ModeratorAction.query().join('user', 'channel')
    query.order_by('timestamp', desc=True)
    paginator = Paginator(templateutil.QueryObjectList(request.connection,
                                                       query), 30)
    page = paginator.page(request.GET.get('page', 1))
    return util.render_to_response(request, 'moderator-history.html', {
        'page': page,
        })

@admin_required
def email_owners(request):
    if request.method != 'POST':
        form = forms.EmailChannelOwnersForm(request.connection)
    else:
        form = forms.EmailChannelOwnersForm(request.connection, request.POST)
        if form.is_valid():
            form.send_email(request.user)
            return util.redirect('moderate')
    return util.render_to_response(request, 'email-channel-owners.html', {
        'form': form})

def get_show_rating_bar(request, channel):
    context = {'channel': channel, 'request':request}
    return loader.render_to_string('guide/show-channel-rating.html', context)

def latest(request, id):
    query = Item.query(Item.c.channel_id == id).order_by(Item.c.date,
                                                  desc=True).limit(1)
    items = query.execute(request.connection)
    if not items:
        raise Http404
    else:
        return util.redirect(items[0].url)

def item(request, id):
    item = util.get_object_or_404(request.connection,
                                  Item.query().join('channel'), id)
    return util.render_to_response(request, 'playback.html',
                                   {'item': item})
