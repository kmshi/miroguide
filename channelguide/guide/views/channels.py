# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django.conf import settings
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.template import loader, context
from django.utils.decorators import decorator_from_middleware
from django.utils.translation import gettext as _

from channelguide import util, cache
from channelguide.cache import client
from channelguide.cache.middleware import AggressiveCacheMiddleware
from channelguide.guide import forms, templateutil, tables
from channelguide.guide.auth import (admin_required, moderator_required,
        login_required)
from channelguide.guide.exceptions import AuthError
from channelguide.guide.models import (Channel, Item, User, FeaturedEmail,
        ModeratorAction, ChannelNote, Rating, Tag, Category, Language,
        FeaturedQueue, GeneratedRatings, Cobranding)
from channelguide.guide.notes import get_note_info, make_rejection_note
from channelguide.guide.emailmessages import EmailMessage
from sqlhelper.sql.statement import Select
from sqlhelper.sql.expression import Literal
from sqlhelper import signals
import re, urllib, time, operator

SESSION_KEY = 'submitted-feed'

@moderator_required
def moderator_channel_list(request, state):
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
    else:
        query.where(state=Channel.NEW)
        header = _("Unreviewed Channels")
    pager =  templateutil.Pager(10, query, request)

    return util.render_to_response(request, 'moderator-channel-list.html', {
        'pager': pager,
        'channels': pager.items,
        'header': header,
        })

def destroy_submit_url_session(request):
    if SESSION_KEY in request.session:
        del request.session[SESSION_KEY]

@login_required
def submit_feed(request):
    destroy_submit_url_session(request)
    if request.method != 'POST':
        form = forms.FeedURLForm(request.connection)
    else:
        form = forms.FeedURLForm(request.connection, request.POST.copy())
        if form.is_valid():
            request.session[SESSION_KEY] = form.get_feed_data()
            return util.redirect("channels/submit/step2")
    return util.render_to_response(request, 'submit-feed-url.html', 
            {'form': form})

@login_required
def submit_channel(request):
    """
    Called when the user is submitting a channel.  If the SESSION_KEY
    cookie isn't set, then we redirect back to the first step.
    XXX: check for clients that don't support cookies

    If the submisstion used the GET method, we create a form that allows
    the submitter to describe the feed in more detail (languages, categories,
    tags, etc.).

    If the submission used the POST method, we check to see if the submitted
    form is valid; if it is we create the channel and redirect to the
    post-submission page.  Otherwise, redisplay the form with the errors
    highlighted.
    """

    if not SESSION_KEY in request.session:
        return util.redirect('channels/submit/step1')
    session_dict = request.session[SESSION_KEY]
    if request.method != 'POST':
        form = forms.SubmitChannelForm(request.connection)
        form.set_defaults(session_dict)
        session_dict['detected_thumbnail'] = form.set_image_from_feed
        request.session.modified = True
    else:
        form = forms.SubmitChannelForm(request.connection, 
                util.copy_post_and_files(request))
        if form.user_uploaded_file():
            session_dict['detected_thumbnail'] = False
            request.session.modified = True
        if form.is_valid():
            feed_url = request.session[SESSION_KEY]['url']
            form.save_channel(request.user, feed_url)
            destroy_submit_url_session(request)
            return util.redirect(settings.BASE_URL_FULL + "channels/submit/after?%s" % feed_url)
        else:
            form.save_submitted_thumbnail()
    context = form.get_template_data()
    if session_dict.get('detected_thumbnail'):
        context['thumbnail_description'] = _("Current image (from the feed)")
    else:
        context['thumbnail_description'] = _("Current image (uploaded)")
    return util.render_to_response(request, 'submit-channel.html', context)

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

@cache.cache_for_user
def show(request, id, featured_form=None):
    query = Channel.query()
    query.join('categories', 'tags', 'owner', 'last_moderated_by', 'rating')
    if request.user.is_supermoderator():
        query.join('featured_queue', 'featured_queue.featured_by')
    item_query = Item.query(channel_id=id).join('channel').order_by('date', desc=True).limit(4)
    c = util.get_object_or_404(request.connection, query, id)
    if c.rating is None:
        c.rating = GeneratedRatings()
        c.rating.channel_id = c.id
        c.rating.count = c.rating.average = c.rating.total = 0
        c.rating.save(request.connection)
    context = {
        'channel': c,
        'items': item_query.execute(request.connection),
        'recommendations': get_recommendations(request, id),
        'show_edit_button': request.user.can_edit_channel(c),
        'show_extra_info': request.user.can_edit_channel(c),
        'link_to_channel': True,
        'BASE_URL': settings.BASE_URL,
        'rating_bar': get_show_rating_bar(request, c),
    }
    if len(c.description.split()) > 73:
        context['shade_description'] =  True
    if 'channel-edit-error' in request.session:
        context['error'] = request.session['channel-edit-error']
        del request.session['channel-edit-error']
    if request.user.is_supermoderator():
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

def after_submit(request):
    url = request.META.get('QUERY_STRING')
    subscribe = util.get_subscription_url(url)
    def link(inside):
        return "<a href='%s' title='Miro: Internet TV'>%s</a>" % (subscribe, inside)
    textLink = '%s' % link("Your 1-Click Subscribe URL")
    buttons = [
        'http://subscribe.getmiro.com/img/buttons/one-click-subscribe-88X34.png',
        'http://subscribe.getmiro.com/img/buttons/one-click-subscribe-109X34.png']
    html = ['<ul><form name="buttoncode">']
    for button in buttons:
        img = "<img src='%s' alt='Miro Video Player' border='0' id='one-click-image' />" % button
        buttonLink = link(img)
        inputName = "btn%i" % len(html)
        wholeButton = '<li>%s<li><span>html:</span><input size="40" id="one-click-link" name="%s" value="%s" onClick="document.buttoncode.%s.select();">' % (img, inputName, buttonLink, inputName)
        html.append(wholeButton)
    html.append('</form>')
    html.append('<li><h3>' + textLink + '</h3>')
    html.append('</ul>')
    context = {
            'html' : ''.join(html),
            }
    return util.render_to_response(request, 'after-submit.html', context)

def subscribe(request, id):
    channel = util.get_object_or_404(request.connection, Channel, id)
    channel.add_subscription(request.connection,
            request.META.get('REMOTE_ADDR', '0.0.0.0'))
    subscribe_url = util.get_subscription_url(channel.url)
    return HttpResponseRedirect(subscribe_url)

def subscribe_hit(request, id):
    """Used by our ajax call handleSubscriptionLink.  It will get a security
    error if we redirect it to a URL outside the channelguide, so we don't do
    that
    """
    ids = [id] + [int(k) for k in request.GET]
    for id in ids:
        channel = util.get_object_or_404(request.connection, Channel, id)
        referer = request.META.get('HTTP_REFERER', '')
        match = re.match(settings.BASE_URL_FULL + 'channels/(\d+)?', referer)
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

def get_recommendations(request, id):
    recSelect = Select('*')
    recSelect.froms.append('cg_channel_recommendations')
    recSelect.wheres.append('channel1_id=%s OR channel2_id=%s' % (id, id))
    recSelect.wheres.append('cosine>=0.025')
    recSelect.order_by.append('cosine DESC')
    elements = recSelect.execute(request.connection)
    recommendations = [e[0] == int(id) and e[1] or e[0] for e in elements]
    channels = []
    for rec in recommendations:
        if len(channels) == 4:
            break
        try:
            chan = Channel.query(user=request.user).get(request.connection, rec)
        except Exception:
            continue
        else:
            channels.append(chan)
    return channels

def rate(request, id):
    if not request.user.is_authenticated():
        if 'HTTP_REFERER' in request.META:
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

class PopularWindowSelect(templateutil.ViewSelect):
    view_choices = [
            ('today', _('Today')),
            ('month', _('Month')),
            ('alltime', _('All-Time')),
    ]

    base_url = util.make_url('channels/popular')

    def default_choice(self):
        return 'today'

    def current_choice_label(self):
        if self.current_choice == 'today':
            return _("Today")
        elif self.current_choice == 'month':
            return _("This Month")
        else:
            return _("All-Time")

@cache.cache_for_user
def popular_view(request):
    timespan = request.GET.get('view', 'today')
    if timespan == 'today':
        count_name = 'subscription_count_today'
    elif timespan == 'month':
        count_name = 'subscription_count_month'
    else:
        timespan = None
        count_name = 'subscription_count'
    query = Channel.query_approved(user=request.user)
    query.join('rating')
    query.load(count_name, 'item_count')
    query.order_by(query.get_column(count_name), desc=True)
    pager = templateutil.Pager(10, query, request)
    for channel in pager.items:
        if timespan == 'today':
            channel.timeline = 'Today'
        elif timespan == 'month':
            channel.timeline = 'This Month'
        else:
            channel.timeline = 'All-Time'
        channel.popular_count = getattr(channel, count_name)
    window_select = PopularWindowSelect(request)
    context = {
            'pager' : pager,
            'timeline' : window_select.current_choice_label(),
            'popular_window_select': window_select
        }
    return util.render_to_response(request, 'popular.html', context)

def make_simple_list(request, query, header, order_by=None):
    if order_by:
        query = query.order_by(order_by)
    pager =  templateutil.Pager(8, query, request)
    return util.render_to_response(request, 'two-column-list.html', {
        'header': header,
        'pager': pager,
    })

@cache.aggresively_cache
def by_name(request):
    query = Channel.query_approved()
    return make_simple_list(request, query, _("Channels By Name"),
            Channel.c.name)


@cache.aggresively_cache
def hd(request):
    query = Channel.query_approved(hi_def=1, user=request.user)
    templateutil.order_channels_using_request(query, request)
    pager =  templateutil.Pager(8, query, request)
    return util.render_to_response(request, 'two-column-list.html', {
        'header': _('HD Channels'),
        'pager': pager,
        'order_select': templateutil.OrderBySelect(request),
    })

@cache.aggresively_cache
def features(request):
    query = Channel.query(user=request.user).join('featured_queue')
    j = query.joins['featured_queue']
    j.where(j.c.state!=0)
    query.order_by(j.c.state).order_by(j.c.featured_at, desc=True)
    return make_simple_list(request, query, _("Featured Channels"))

def get_toprated_query(user):
    query = Channel.query_approved(user=user)
    query.join('rating')
    query.joins['rating'].where(query.joins['rating'].c.count > 3)
    query.load('item_count', 'subscription_count_today')
    query.order_by(query.joins['rating'].c.average, desc=True)
    query.order_by(query.joins['rating'].c.count, desc=True)
    return query

@cache.cache_for_user
def toprated(request):
    query = get_toprated_query(request.user)
    pager = templateutil.Pager(10, query, request)
    for channel in pager.items:
        channel.popular_count = channel.subscription_count_today
        channel.timeline = 'Today'
    context = {'pager': pager,
            'title': 'Top Rated Channels'
        }
    return util.render_to_response(request, 'popular.html', context)

def group_channels_by_date(channels):
    if channels is None:
        return []
    current_date = None
    channels_in_date = []
    retval = []

    for channel in channels:
        channel_date = channel.approved_at.date()
        if channel_date != current_date:
            if channels_in_date:
                retval.append({'date': current_date, 
                    'channels': channels_in_date})
            current_date = channel_date
            channels_in_date = [channel]
        else:
            channels_in_date.append(channel)
    if channels_in_date:
        retval.append({'date': current_date, 'channels': channels_in_date})
    return retval

@cache.aggresively_cache
def recent(request):
    query = Channel.query_new(user=request.user)
    pager =  templateutil.Pager(8, query, request)
    return util.render_to_response(request, 'recent.html', {
        'header': "RECENT CHANNELS",
        'pager': pager,
        'channels_by_date': group_channels_by_date(pager.items),
    })

def for_user(request, user_id):
    user = util.get_object_or_404(request.connection, User, user_id)
    query = Channel.query(owner_id=user.id, user=request.user)
    query.join('owner', 'last_moderated_by', 'featured_queue', 'featured_queue.featured_by')
    query.order_by(Channel.c.name)
    if request.user.is_admin() or request.user.id == user_id:
        try:
            cobrand = Cobranding.get(request.connection, user.username)
        except:
            cobrand = None
    else:
        cobrand = None
    pager =  templateutil.Pager(10, query, request)
    return util.render_to_response(request, 'for-user.html', {
        'for_user': user,
        'cobrand': cobrand,
        'channels': pager.items,
        'pager': pager,
        })

def edit_channel(request, id):
    query = Channel.query()
    query.join('language', 'secondary_languages', 'categories', 'notes',
            'notes.user')
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
    common_footer ="""If you want to show off your featured channel, you can link to this page: https://www.miroguide.com/channels/features

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
    pager =  templateutil.Pager(30, query, request)
    return util.render_to_response(request, 'moderator-history.html', {
        'pager': pager,
        'actions': pager.items,
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


