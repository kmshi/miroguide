# Copyright (c) 2009 Participatory Culture Foundation
# See LICENSE for details.

from django.conf import settings
from django.core import cache
from django.contrib.auth.models import User
from django.db.models import Q
from channelguide.search import utils as search_mod
from channelguide.channels.models import Channel, AddedChannel, Item
from channelguide.labels.models import Category, Language
from channelguide.ratings.models import Rating
from channelguide.recommendations.models import Similarity

import operator
import time

def login(id):
    try:
        user = User.objects.get(pk=id)
    except User.DoesNotExist:
        return None
    return user

def get_item(id):
    itemKey = 'Item:%s' % id
    timestamp = cache.cache.get(itemKey)
    if timestamp is None:
        timestamp = time.time()
        cache.cache.set(itemKey, timestamp)
    apiKey = 'get_item:%s:%s' % (id, timestamp)
    item = cache.cache.get(apiKey)
    if item is None or not hasattr(item, '_state'):
        try:
            item = Item.objects.get(pk=id)
        except Item.DoesNotExist:
            raise LookupError('item %s does not exist' % id)
        cache.cache.set(apiKey, item)
    return item

def get_item_by_url(url):
    try:
        return Item.objects.get(url=url)
    except Item.DoesNotExist:
        raise LookupError('item %s does not exist' % url)

def get_channel(id):
    channelKey = 'Channel:%s' % id
    timestamp = cache.cache.get(channelKey)
    if timestamp is None:
        timestamp = time.time()
        cache.cache.set(channelKey, timestamp)
    apiKey = 'get_channel:%s:%s' % (id, timestamp)
    channel = cache.cache.get(apiKey)
    if channel is None or not hasattr(channel, '_state'):
        try:
            channel = Channel.objects.select_related().get(pk=id)
        except Channel.DoesNotExist:
            raise LookupError('channel %s does not exist' % id)
        cache.cache.set(apiKey, channel)
    return channel

def get_channel_by_url(url):
    try:
        return Channel.objects.select_related().get(url=url)
    except Channel.DoesNotExist:
        raise LookupError('channel %s does not exist' % url)


def get_channels_query(request, filter_list, value_list, sort=None,
                       country_code=None):
    if request.user.has_perm('channels.change_channel'):
        query = Channel.objects.all()
    else:
        query = Channel.objects.approved()
    if isinstance(filter_list, basestring):
        filter_list = [filter_list]
        value_list = [value_list]
    for filter, value in zip(filter_list, value_list):
        if filter == 'audio':
            if value:
                query = query.filter(state=Channel.AUDIO)
            else:
                query = query.exclude(state=Channel.AUDIO)
        elif filter == 'category':
            query = query.filter(categories__name=value)
        elif filter == 'tag':
            query = query.filter(tags__name=value)
        elif filter == 'language':
            query = query.filter(language__name=value)
        elif filter == 'featured':
            query = query.filter(featured=bool(value))
        elif filter == 'hd':
            query = query.filter(hi_def=bool(value))
        elif filter == 'feed':
            query = query.filter(url__isnull=not bool(value))
        elif filter == 'user':
            query = query.filter(owner__username=value)
        elif filter == 'name':
            if value is not None:
                query = query.filter(name__istartswith=value)
        elif filter == 'search':
            query = search_mod.search_channels(query, value.split())
        else:
            raise ValueError('unknown filter: %r' % (filter,))
    if country_code:
        query = query.filter(Q(geoip='') |
                             Q(geoip__icontains=country_code))
    if 'search' not in filter_list: # searches are already sorted
        if sort is not None and sort[0] == '-':
            desc = '-'
            sort = sort[1:]
        else:
            desc = ''
        if not sort:
            sort = 'name' # default to sorting by name
        if sort in ('name', 'id'):
            pass # sort is already what we'll use in order_by
        elif sort == 'age':
            sort = 'approved_at'
        elif sort == 'popular':
            sort = 'stats__subscription_count_today'
        elif sort == 'rating':
            query = query.filter(rating__count__gt=5).extra(
                select={
                    'rating__bayes':
                        """
cg_channel_generated_ratings.average * (cg_channel_generated_ratings.count /
    (cg_channel_generated_ratings.count + 5)) +
(SELECT SUM(total)/SUM(count)
 FROM cg_channel_generated_ratings) * (5 /
    (cg_channel_generated_ratings.count + 5))"""})
            sort = 'rating__bayes'
        else:
            raise ValueError('unknown sort type: %r' % sort)
        query = query.order_by('archived', desc + sort)
    if 'language' not in filter_list:
        if request.user.is_authenticated():
            profile = request.user.get_profile()
            if profile.filter_languages and profile.shown_languages.count():
                query = query.filter(language__in=
                                    profile.shown_languages.all())
        elif request.session.get('filter_languages'):
            languageName = settings.ENGLISH_LANGUAGE_MAP.get(
                request.LANGUAGE_CODE)
            if languageName:
                dbLanguages = Language.objects.filter(name=languageName)
                if dbLanguages:
                    query = query.filter(language__in=dbLanguages)
    return query

def _use_sort(sort):
    """
    For sorts that actually returns counts (count, ratingcount), this returns
    the sort that we should actually use.
    """
    if sort == 'count':
        return 'name'
    elif sort == 'ratingcount':
        return 'rating'
    else:
        return sort

def _add_limit_and_offset(query, limit, offset):
    if limit is None:
        limit = 20
    if limit > 100:
        limit = 100
    if offset is None or offset < 0:
        offset = 0
    return list(query[offset:offset+limit])

def get_feeds(request, filter, value, sort=None, limit=None, offset=None,
              loads=None, country_code=None):
    use_sort = _use_sort(sort)
    query = get_channels_query(request, filter, value, use_sort,
                               country_code)
    if query is not None:
        query = query.filter(url__isnull=False)
    if sort != use_sort:
        if query is not None:
            return query.count()
        else:
            return 0
    elif query is None:
        return []
    return _add_limit_and_offset(query, limit, offset)

def get_sites(request, filter, value, sort=None, limit=None, offset=None,
              loads=None, country_code=None):
    use_sort = _use_sort(sort)
    query = get_channels_query(request, filter, value, use_sort,
                               country_code)
    if query is not None:
        query = query.filter(url__isnull=True)
    if sort != use_sort:
        if query is not None:
            return query.count()
        else:
            return 0
    elif query is None:
        return []
    return _add_limit_and_offset(query, limit, offset)

def get_channels(request, filter, value, sort=None, limit=None, offset=None,
        loads=None, country_code=None):
    """
    The old API method which returns a list of channels.  With the redesign and
    the inclusion of sites, you should use either get_feeds or get_sites.
    """
    use_sort = _use_sort(sort)

    query = get_channels_query(
        request, filter, value, sort=use_sort, country_code=country_code
    )

    if sort != use_sort:
        if query is not None:
            return query.count()
        else:
            return 0
    elif query is None:
        return []
    return _add_limit_and_offset(query, limit, offset)

def search(terms):
    return search_mod.search_channels(Channel.objects.approved(), terms)

def rate(user, channel, score):
    rating, created = Rating.objects.get_or_create(user=user,
                                                   channel=channel)
    try:
        rating.rating = int(score)
    except (ValueError, TypeError):
        return
    else:
        if not rating.rating:
            rating.rating = None
        rating.save()

def get_rating(user, channel):
    try:
        r = Rating.objects.get(user=user, channel=channel)
    except Rating.DoesNotExist:
        return
    else:
        return r.rating

def get_ratings(user, rating=None):
    if rating is None:
        return dict((r.channel, r.rating) for r in
                    Rating.objects.select_related().filter(user=user.id))
    else:
        return [r.channel for r in
                Rating.objects.select_related().filter(user=user,
                                                       rating=rating)]

def get_recommendations(user, start=0, length=10, filter=None):
    ratings = Rating.objects.filter(user=user).order_by('-timestamp')
    added_channels = AddedChannel.objects.filter(user=user).order_by(
        '-timestamp')
    if ratings.count():
        if added_channels.count():
            key = str(
                max(ratings[0].timestamp,
                    added_channels[0].timestamp).isoformat())
        else:
            key = str(ratings[0].timestamp.isoformat())
        cacheKey = ':'.join(('recommendations_for', str(user.id),
                             key))
        result = cache.cache.get(cacheKey)
        if result is None:
            (estimatedRatings,
             reasons) = Similarity.objects.recommend_from_ratings(
                ratings)
            added_ids = [added.channel_id for added in added_channels]
            toSort = estimatedRatings.items()
            toSort.sort(key=operator.itemgetter(1), reverse=True)
            ids = [cid for (cid, rating) in toSort if rating>=3.25 and
                   cid not in added_ids]
            ids = ids[:99]
            for id in estimatedRatings.keys():
                if id not in ids:
                    del estimatedRatings[id]
            for id in reasons.keys():
                if id not in ids:
                    del reasons[id]
            result = estimatedRatings, reasons, ids
            cache.cache.set(cacheKey, result)
        else:
            estimatedRatings, reasons, ids = result
        if not ids:
            if start is None:
                return 0
            else:
                return []
        query = Channel.objects.filter(id__in=ids)
        if filter is not None:
            if filter == 'feed':
                query = query.filter(url__isnull=False)
            elif filter == 'site':
                query = query.filter(url__isnull=True)
            else:
                raise ValueError('unknown recommendations filter: %r' % filter)
        if start is None:
            if not ids:
                return 0
            else:
                return query.count()
        profile = user.get_profile()
        if profile.filter_languages:
            query = query.filter(
                language__in=profile.shown_languages.all())
        channels = list(query)
        for channel in channels:
            channel.guessed = estimatedRatings[channel.id]
            if channel.id in reasons:
                channelReasons = dict((cid, score) for (score, cid) in
                                      reasons[channel.id][-3:])
                channel.reasons = list(Channel.objects.filter(
                        id__in=channelReasons.keys()))
                for reason in channel.reasons:
                    reason.score = channelReasons[reason.id]
                channel.reasons.sort(key=operator.attrgetter('score'),
                                     reverse=True)
        channels.sort(key=operator.attrgetter('guessed'), reverse=True)
        return channels[start:start+length]
    else:
        if start is None:
            return 0
        else:
            return []

def list_labels(type):
    if type == 'category':
        model = Category
    elif type == 'language':
        model = Language
    else:
        raise ValueError("type must be 'category' or 'language'")
    return model.objects.order_by('name')
