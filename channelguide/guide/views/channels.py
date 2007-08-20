from django.conf import settings
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.utils.translation import gettext as _

from channelguide import util, cache
from channelguide.guide import forms, templateutil
from channelguide.guide.auth import (admin_required, moderator_required,
        login_required)
from channelguide.guide.models import (Channel, Item, User, ModeratorAction,
        ChannelNote)
from channelguide.guide.notes import get_note_info, make_rejection_note

import urllib

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
            return util.redirect("channels/submit/after?%s" % feed_url)
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
        elif action == 'feature':
            request.user.check_is_supermoderator()
            count = Channel.query(featured=True).count(request.connection)
            if count < settings.MAX_FEATURES:
                channel.featured = True
            else:
                msg = _("Can't feature more than %s channels") % \
                        settings.MAX_FEATURES
                request.session['channel-edit-error'] = msg
        elif action == 'unfeature':
            request.user.check_is_supermoderator()
            channel.featured = False
        elif action == 'change-state':
            request.user.check_is_moderator()
            submit_value = request.POST['submit']
            if submit_value == 'Approve':
                channel.join('owner').execute(request.connection)
                newstate = Channel.APPROVED
            elif submit_value == "Don't Know":
                newstate = Channel.DONT_KNOW
            elif submit_value == 'Unapprove':
                newstate = Channel.NEW
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
            title = request.POST.get('title')
            body = request.POST.get('body')
            if title and body:
                note = ChannelNote(request.user, title, body,
                        ChannelNote.MODERATOR_TO_OWNER)
                note.channel = channel
                note.save(request.connection)
                note.send_email(request.connection)
                channel.change_state(request.user, Channel.REJECTED,
                        request.connection)
            else:
                msg = _("Rejection emails need a title and body")
                request.session['channel-edit-error'] = msg
        channel.save(request.connection)
    return util.redirect_to_referrer(request)

def show(request, id):
    query = Channel.query()
    query.join('categories', 'tags', 'notes', 'owner', 'last_moderated_by',
            'notes.user')
    item_query = Item.query(channel_id=id).order_by('date', desc=True)
    context = {
        'channel': util.get_object_or_404(request.connection, query, id),
        'items': item_query.limit(6).execute(request.connection),
    }
    context['notes'] = get_note_info(context['channel'], request.user)
    if 'channel-edit-error' in request.session:
        context['error'] = request.session['channel-edit-error']
        del request.session['channel-edit-error']
    return util.render_to_response(request, 'show-channel.html', context)

def after_submit(request):
    url = request.META.get('QUERY_STRING')
    subscribe = "http://subscribe.getMiro.com/?url1=%s" % urllib.quote_plus(url)
    def link(inside):
        return '<a href="%s" title="Miro: Internet TV">%s</a>' % (subscribe, inside)
    textLink = '<h3>%s</h3>' % link("1-Click Link")
    buttons = [
        'http://subscribe.getmiro.com/img/buttons/one-click-subscribe-88X34.png',
        'http://subscribe.getmiro.com/img/buttons/one-click-subscribe-109X34.png']
    html = [textLink]
    for button in buttons:
        img = '<img src="%s" alt="Miro Video Player" border="0" id="one-click-image" />' % button
        buttonLink =link(img)
        wholeButton = '%s<textarea id="one-click-link" cols="50" rows="2" style="background-color:#EEEEEE;">%s</textarea>' % (img, buttonLink)
        html.append(wholeButton)
    context = {
            'html' : ''.join(html),
            }
    return util.render_to_response(request, 'after-submit.html', context)

def subscribe(request, id):
    channel = util.get_object_or_404(request.connection, Channel, id)
    channel.add_subscription(request.connection,
            request.META.get('REMOTE_ADDR', '0.0.0.0'))
    subscribe_url = settings.SUBSCRIBE_URL % { 'url': channel.url }
    return HttpResponseRedirect(subscribe_url)

def subscribe_hit(request, id):
    """Used by our ajax call handleSubscriptionLink.  It will get a security
    error if we redirect it to a URL outside the channelguide, so we don't do
    that
    """
    channel = util.get_object_or_404(request.connection, Channel, id)
    channel.add_subscription(request.connection,
            request.META.get('REMOTE_ADDR', '0.0.0.0'))
    return HttpResponse("Hit successfull")

class PopularWindowSelect(templateutil.ViewSelect):
    view_choices = [
            ('today', _('Today')),
            ('month', _('Month')),
            ('alltime', _('All-Time')),
    ]

    base_url = util.make_url('channels/popular')

    def default_choice(self):
        return 'month'

    def current_choice_label(self):
        if self.current_choice == 'today':
            return _("Today")
        elif self.current_choice == 'month':
            return _("This Month")
        else:
            return _("All-Time")

@cache.aggresively_cache
def popular(request):
    timespan = request.GET.get('view', 'month')
    if timespan == 'today':
        count_name = 'subscription_count_today'
    elif timespan == 'month':
        count_name = 'subscription_count_month'
    else:
        count_name = 'subscription_count'
    query = Channel.query_approved().load(count_name)
    query.order_by(count_name, desc=True)
    if count_name != 'subscription_count':
        query.load('subscription_count')
        query.order_by('subscription_count', desc=True)
    pager =  templateutil.Pager(10, query, request)
    for channel in pager.items:
        channel.popular_count = getattr(channel, count_name)
    return util.render_to_response(request, 'popular.html', {
        'pager': pager,
        'popular_window_select': PopularWindowSelect(request)
    })

def make_simple_list(request, query, header, order_by):
    pager =  templateutil.Pager(8, query.order_by(order_by), request)
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
    query = Channel.query_approved(hi_def=1)
    templateutil.order_channels_using_request(query, request)
    pager =  templateutil.Pager(8, query, request)
    return util.render_to_response(request, 'two-column-list.html', {
        'header': _('HD Channels'),
        'pager': pager,
        'order_select': templateutil.OrderBySelect(request),
    })

@cache.aggresively_cache
def features(request):
    query = Channel.query_approved(featured=1)
    return make_simple_list(request, query, _("Featured Channels"),
            Channel.c.featured_at)

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
    query = Channel.query_approved().order_by('approved_at', desc=True)
    pager =  templateutil.Pager(8, query, request)
    return util.render_to_response(request, 'recent.html', {
        'header': "RECENT CHANNELS",
        'pager': pager,
        'channels_by_date': group_channels_by_date(pager.items),
    })


def for_user(request, user_id):
    user = util.get_object_or_404(request.connection, User, user_id)
    query = Channel.query(owner_id=user.id)
    query.join('categories', 'tags', 'owner', 'last_moderated_by')
    pager =  templateutil.Pager(10, query, request)
    return util.render_to_response(request, 'for-user.html', {
        'for_user': user,
        'channels': pager.items,
        'pager': pager,
        })

def edit_channel(request, id):
    query = Channel.query()
    query.join('language', 'secondary_languages', 'categories')
    channel = util.get_object_or_404(request.connection, query, id)
    request.user.check_can_edit(channel)
    if request.method != 'POST':
        form = forms.EditChannelForm(request, channel)
    else:
        form = forms.EditChannelForm(request, channel,
                util.copy_post_and_files(request))
        if form.is_valid():
            form.update_channel(channel)
            return util.redirect(channel.get_absolute_url())
        else:
            form.save_submitted_thumbnail()
    context = form.get_template_data()
    if form.set_image_from_channel:
        context['thumbnail_description'] = _("Current image (no change)")
    else:
        context['thumbnail_description'] = _("Current image (uploaded)")
    return util.render_to_response(request, 'edit-channel.html', context)

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
