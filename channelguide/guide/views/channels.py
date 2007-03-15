import urllib
import random
import re

from django.conf import settings
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.utils.translation import gettext as _
from sqlalchemy import desc, eagerload, func, and_, select, null

from submitform import SubmitChannelForm
from feedform import FeedURLForm
from models import Channel, Category, Tag, Item
import tables
from channelguide import util
from channelguide.auth.models import User
from channelguide.auth.decorators import moderator_required, login_required
from channelguide.blogtrack.models import PCFBlogPost
from channelguide.languages.models import Language
from channelguide.notes.models import ChannelNote, ModeratorPost
from channelguide.notes.util import get_note_info
from channelguide.templatehelpers import Pager, ViewSelect

SESSION_KEY = 'submitted-feed'

def get_popular_channels(channel_query, count):
   select = channel_query.select_by(state=Channel.APPROVED)
   return select.order_by(desc(Channel.c.subscription_count))[:count]

def get_featured_channels(channel_query):
   select = channel_query.select_by(state=Channel.APPROVED, featured=1)
   return select.order_by(func.rand())

def get_new_channels(channel_query, count):
   select = channel_query.select_by(state=Channel.APPROVED)
   return select.order_by(desc(Channel.c.approved_at))[:count]

def get_category_channels(channel_query, category, count):
    select = channel_query.select_by(state='A')
    select = select.filter(channel_query.join_to('categories'))
    select = select.filter(Category.c.id == category.id)
    return util.select_random(select, count)

def get_peeked_category(category_query, get_params):
    try:
        dir, name = get_params['category_peek'].split(':')
    except:
        return util.select_random(category_query.select(), 1)[0]
    if dir == 'after':
        select = category_query.select(Category.c.name > name,
                order_by=Category.c.name)
    else:
        select = category_query.select(Category.c.name < name,
                order_by=desc(Category.c.name))
    try:
        return select[0]
    except IndexError:
        if dir == 'after':
            return category_query.select(order_by=Category.c.name)[0]
        else:
            return category_query.select(order_by=desc(Category.c.name))[0]

def make_category_peek(request):
    channel_query = request.db_session.query(Channel)
    category_query = request.db_session.query(Category)
    try:
        category = get_peeked_category(category_query, request.GET)
    except IndexError: # no categories defined
        return None
    name = urllib.quote_plus(category.name)
    return {
            'category': category,
            'channels': get_category_channels(channel_query, category, 6),
            'prev_url': '?category_peek=before:%s' % name,
            'next_url': '?category_peek=after:%s' % name,
            'prev_url_ajax': 'category-peek-fragment?category_peek=before:%s' % name,
            'next_url_ajax': 'category-peek-fragment?category_peek=after:%s' % name,
    }

def index(request):
    channel_query = request.db_session.query(Channel)
    category_query = request.db_session.query(Category)
    post_query = request.db_session.query(PCFBlogPost,
            order_by=PCFBlogPost.c.position)

    return util.render_to_response(request, 'channels/index.html', {
        'popular_channels': get_popular_channels(channel_query, 7),
        'new_channels': get_new_channels(channel_query, 7),
        'featured_channels': get_featured_channels(channel_query),
        'category_peek': make_category_peek(request),
        'blog_posts': post_query.select(limit=3),
        'categories': category_query.select(order_by=Category.c.name),
    })

def category_peek_fragment(request):
    return util.render_to_response(request, 'channels/category-peek.html', {
        'category_peek': make_category_peek(request),
    })

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

    return util.render_to_response(request, 'channels/moderate.html', context)

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

    return util.render_to_response(request, 'channels/unapproved-list.html', {
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
        form = FeedURLForm(request.db_session)
    else:
        form = FeedURLForm(request.db_session, request.POST.copy())
        if form.is_valid():
            request.session[SESSION_KEY] = form.get_feed_data()
            return util.redirect("channels/submit/step2")
    return util.render_to_response(request, 'channels/submit-feed.html', 
            {'form': form})

@login_required
def submit_channel(request):
    if not SESSION_KEY in request.session:
        return util.redirect('channels/submit/step1')
    session_dict = request.session[SESSION_KEY]
    if request.method != 'POST':
        form = SubmitChannelForm(request.db_session)
        form.set_defaults(session_dict)
        session_dict['detected_thumbnail'] = form.set_image_from_feed
        request.session.modified = True
    else:
        form = SubmitChannelForm(request.db_session, 
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
    context['detected_thumbnail'] = session_dict.get('detected_thumbnail',
            False)
    return util.render_to_response(request, 'channels/submit.html', context)

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
    return util.render_to_response(request, 'channels/show-channel.html', {
        'channel': channel,
        'notes': get_note_info(channel, request.user),
        'items': items.order_by(Item.c.date)[:6],
    })

def after_submit(request):
    return util.render_to_response(request, 'channels/after-submit.html')

def subscribe(request, id):
    channel = util.get_object_or_404(request.db_session.query(Channel), id)
    channel.add_subscription(request.connection)
    subscribe_url = settings.SUBSCRIBE_URL % { 'url': channel.url }
    return HttpResponseRedirect(subscribe_url)

def all_tags(request):
    q = request.db_session.query(Tag)
    select = q.select(order_by=desc(Tag.c.channel_count))
    pager =  Pager(45, select, request)
    return util.render_to_response(request, 'channels/tag-list.html', {
        'pager': pager,
    })

def all_categories(request):
    q = request.db_session.query(Category)
    select = q.select(order_by=desc(Category.c.channel_count))
    return util.render_to_response(request, 'channels/group-list.html', {
        'group_name': _('Categories'),
        'groups': select,
    })

class OrderBySelect(ViewSelect):
    view_choices = [
            ('popular', _('Most Popular')),
            ('date', _('Most Recent')),
            ('alphabetical', _('A-Z')),
    ]

    def __init__(self, request, base_url):
        self.base_url = base_url
        super(OrderBySelect, self).__init__(request)

def make_two_column_list(request, id, class_, header_string, join_path=None, 
        join_clause=None):
    """Handles making pages for tags/categories/languages."""

    group = util.get_object_or_404(request.db_session.query(class_), id)
    order_by = request.GET.get('view', 'popular')
    query = request.db_session.query(Channel)
    select = query.select_by(state=Channel.APPROVED)
    if join_path:
        select = select.filter(query.join_via(join_path))
    if join_clause:
        select = select.filter(join_clause)
    select = select.filter(class_.c.id==id)
    if order_by == 'alphabetical':
        select = select.order_by(Channel.c.name)
    elif order_by == 'popular':
        select = select.order_by(desc(Channel.c.subscription_count))
    else:
        select = select.order_by(desc(Channel.c.modified))
    pager =  Pager(8, select, request)
    return util.render_to_response(request, 'channels/two-column-list.html', {
        'header': header_string % group, 
        'pager': pager,
        'order_select': OrderBySelect(request, group.get_absolute_url()),
    })

def tag(request, id):
    return make_two_column_list(request, id, Tag, _('Tag: %s'),
            join_path=['tags'])

def category(request, id):
    return make_two_column_list(request, id, Category, _('Category: %s'), 
            join_path=['categories'])

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
    return util.render_to_response(request, 'channels/popular.html', {
        'window': window,
        'pager': pager,
        'popular_window_select': PopularWindowSelect(request)
    })

def make_simple_list(request, query, header, order_by):
    select = query.order_by(order_by)
    pager =  Pager(8, select, request)
    return util.render_to_response(request, 'channels/two-column-list.html', {
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
    return util.render_to_response(request, 'channels/recent.html', {
        'header': "RECENT CHANNELS",
        'pager': pager,
        'channels_by_date': group_channels_by_date(pager.items),
    })


def get_search_terms(query):
    return [term for term in re.split("\s", query.strip())]

def terms_too_short(terms):
    return len([term for term in terms if len(term) >= 3]) == 0

def search_results(session, class_, terms, search_attribute='name'):
    select = session.query(class_).select()
    if class_ is not Language:
        select = select.filter(class_.c.channel_count > 0)
    else:
        select = select.filter((class_.c.channel_count_primary > 0) |
                (class_.c.channel_count_secondary > 0))

    search_column = class_.c[search_attribute]
    for term in terms:
        select = select.filter(search_column.like('%s%%' % term))
    return select.list()

def search(request):
    CHANNEL_LIMIT = 10
    CHANNEL_ITEM_MATCH_LIMIT = 20
    try:
        query = request.GET['query']
    except:
        raise Http404

    terms = get_search_terms(query)
    if terms_too_short(terms):
        return util.render_to_response(request, 'channels/search.html', {})

    href = 'search-more-channels?query=' + urllib.quote_plus(query)
    label = _('More channels with videos that match this search.')
    more_channels_link = util.make_link(href, label)
    channels = Channel.search(request.db_session, terms,
            limit=CHANNEL_LIMIT)
    channels_count = Channel.count_search_results(request.connection, terms)
    channels_with_items = Channel.search_items(request.db_session, terms,
            limit=CHANNEL_ITEM_MATCH_LIMIT+1)

    return util.render_to_response(request, 'channels/search.html', {
        'channels': channels,
        'channels_count': channels_count,
        'extra_channels': channels_count > CHANNEL_LIMIT,
        'channels_with_items': channels_with_items[:CHANNEL_ITEM_MATCH_LIMIT],
        'extra_channels_with_items': 
            len(channels_with_items) > CHANNEL_ITEM_MATCH_LIMIT,
        'tags': search_results(request.db_session, Tag, terms),
        'languages': search_results(request.db_session, Language, terms),
        'categories': search_results(request.db_session, Category, terms),
        'search_query': query.strip(),
        'more_channels_link': more_channels_link,
        })

def search_more(request):
    try:
        query = request.GET['query']
    except:
        raise Http404

    terms = get_search_terms(query)
    if terms_too_short(terms):
        return util.render_to_response(request, 'channels/search-more.html', {})

    return util.render_to_response(request, 'channels/search-more.html', {
        'initial_search_query': query.strip(),
        'channels': Channel.search(request.db_session, terms),
        'channels_with_items': Channel.search_items(request.db_session,
            terms),
        })
