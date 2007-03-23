from django.conf import settings
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.utils.translation import gettext as _
from sqlalchemy import desc, eagerload, null

from channelguide import util
from channelguide.guide import forms
from channelguide.guide.auth import moderator_required, login_required
from channelguide.guide.models import Channel, Item, ModeratorPost, User
from channelguide.guide.notes import get_note_info
from channelguide.guide.templateutil import Pager, ViewSelect

SESSION_KEY = 'submitted-feed'

@moderator_required
def moderate(request):
    context = {}

    q = request.db_session.query(Channel)
    select = q.select().filter(Channel.c.moderator_shared_at != null())
    select = select.order_by(desc(Channel.c.moderator_shared_at))
    context['shared_channels'] = select[:5]

    context['new_count'] = q.select_by(state=Channel.NEW).count()
    context['dont_know_count'] = q.select_by(state=Channel.DONT_KNOW).count()
    context['waiting_count'] = q.select_by(state=Channel.WAITING).count()
    context['rejected_count'] = q.select_by(state=Channel.REJECTED).count()

    q = request.db_session.query(ModeratorPost)
    select = q.select(order_by=desc(ModeratorPost.c.created_at))
    context['latest_posts'] = select[:5]

    return util.render_to_response(request, 'moderate.html', context)

@moderator_required
def unapproved_channels(request, state):
    q = request.db_session.query(Channel, order_by=Channel.c.creation_time)
    if state == 'waiting':
        select = q.select_by(state=Channel.WAITING)
        header = _("Channels Waiting For Replies")
    elif state == 'dont-know':
        select = q.select_by(state=Channel.DONT_KNOW)
        header = _("Channels Flagged Don't Know By a Moderator")
    elif state == 'rejected':
        select = q.select_by(state=Channel.REJECTED)
        header = _("Rejected Channels")
    else:
        select = q.select_by(state=Channel.NEW)
        header = _("Unreviewed Channels")
    pager =  Pager(10, select, request)

    return util.render_to_response(request, 'unapproved-list.html', {
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
        form = forms.FeedURLForm(request.db_session)
    else:
        form = forms.FeedURLForm(request.db_session, request.POST.copy())
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
        form = forms.SubmitChannelForm(request.db_session)
        form.set_defaults(session_dict)
        session_dict['detected_thumbnail'] = form.set_image_from_feed
        request.session.modified = True
    else:
        form = forms.SubmitChannelForm(request.db_session, 
                util.copy_post_and_files(request))
        if form.user_uploaded_file():
            session_dict['detected_thumbnail'] = False
            request.session.modified = True
        if form.is_valid():
            feed_url = request.session[SESSION_KEY]['url']
            form.save_channel(request.user, feed_url)
            destroy_submit_url_session(request)
            return util.redirect("channels/submit/after")
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
        query = request.db_session.query(Channel)
        channel = util.get_object_or_404(query, id)
        action = request.POST.get('action')
        if action == 'toggle-moderator-share':
            request.user.check_is_moderator()
            channel.toggle_moderator_share()
        elif action == 'change-state':
            submit_value = request.POST['submit']
            if submit_value == 'Approve':
                newstate = Channel.APPROVED
            elif submit_value == 'Reject':
                newstate = Channel.REJECTED
            elif submit_value == "Sent message":
                newstate = Channel.WAITING
            elif submit_value == "Don't Know":
                newstate = Channel.DONT_KNOW
            elif submit_value == 'Unapprove':
                newstate = Channel.NEW
            else:
                newstate = None
            if newstate is not None:
                channel.change_state(newstate)
                request.user.add_moderator_action(channel, newstate)
    return util.redirect_to_referrer(request)

def show(request, id):
    query = request.db_session.query(Channel)
    query = query.options(eagerload('categories'), eagerload('tag_maps.tag'))
    channel = util.get_object_or_404(query, id)
    items = request.db_session.query(Item).select_by(channel_id=id)
    return util.render_to_response(request, 'show-channel.html', {
        'channel': channel,
        'notes': get_note_info(channel, request.user),
        'items': items.order_by(Item.c.date)[:6].list(),
    })

def after_submit(request):
    return util.render_to_response(request, 'after-submit.html')

def subscribe(request, id):
    channel = util.get_object_or_404(request.db_session.query(Channel), id)
    channel.add_subscription(request.connection)
    subscribe_url = settings.SUBSCRIBE_URL % { 'url': channel.url }
    return HttpResponseRedirect(subscribe_url)

def subscribe_hit(request, id):
    """Used by our ajax call handleSubscriptionLink.  It will get a security
    error if we redirect it to a URL outside the channelguide, so we don't do
    that
    """
    channel = util.get_object_or_404(request.db_session.query(Channel), id)
    channel.add_subscription(request.connection)
    return HttpResponse("Hit successfull")

class PopularWindowSelect(ViewSelect):
    view_choices = [
            ('today', _('Today')),
            ('month', _('Month')),
            ('alltime', _('All-Time')),
    ]

    base_url = util.make_absolute_url('channels/popular')

    def current_choice_label(self):
        if self.current_choice == 'today':
            return _("Today")
        elif self.current_choice == 'month':
            return _("This Month")
        else:
            return _("All-Time")

def popular(request):
    window = request.GET.get('view', 'today')
    query = request.db_session.query(Channel)
    if window == 'today':
        count_name = 'subscription_count_today'
    elif window == 'month':
        count_name = 'subscription_count_month'
    else:
        count_name = 'subscription_count'
    select = query.select_by(state=Channel.APPROVED)
    order_by = [desc(Channel.c[count_name])]
    if count_name != 'subscription_count':
        order_by.append(desc(Channel.c.subscription_count))
    select = select.order_by(order_by)
    pager =  Pager(10, select, request)
    for channel in pager.items:
        channel.popular_count = getattr(channel, count_name)
    return util.render_to_response(request, 'popular.html', {
        'window': window,
        'pager': pager,
        'popular_window_select': PopularWindowSelect(request)
    })

def make_simple_list(request, query, header, order_by):
    select = query.order_by(order_by)
    pager =  Pager(8, select, request)
    return util.render_to_response(request, 'two-column-list.html', {
        'header': header,
        'pager': pager,
    })

def by_name(request):
    query = request.db_session.query(Channel).select_by(state=Channel.APPROVED)
    return make_simple_list(request, query, _("Channels By Name"),
            Channel.c.name)

def features(request):
    query = request.db_session.query(Channel)
    query = query.select_by(state=Channel.APPROVED, featured=1)
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

def recent(request):
    query = request.db_session.query(Channel)
    select = query.select_by(state=Channel.APPROVED)
    select = select.order_by(desc(Channel.c.approved_at))
    pager =  Pager(8, select, request)
    return util.render_to_response(request, 'recent.html', {
        'header': "RECENT CHANNELS",
        'pager': pager,
        'channels_by_date': group_channels_by_date(pager.items),
    })


def for_user(request, user_id):
    user_query = request.db_session.query(User)
    channel_query = request.db_session.query(Channel)
    user = util.get_object_or_404(user_query, user_id)
    select = channel_query.select_by(owner=user)
    pager =  Pager(10, select, request)

    return util.render_to_response(request, 'for-user.html', {
        'for_user': user,
        'channels': pager.items,
        'pager': pager,
        })

def edit_channel(request, id):
    query = request.db_session.query(Channel)
    channel = util.get_object_or_404(query, id)
    request.user.check_can_edit(channel)
    if request.method != 'POST':
        form = forms.EditChannelForm(request.db_session, channel)
    else:
        form = forms.EditChannelForm(request.db_session, channel,
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
