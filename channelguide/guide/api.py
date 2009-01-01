from channelguide.guide.models import (Category, Channel, Language, Tag, Rating,
                                       User, AddedChannel)
from channelguide.guide import recommendations
from channelguide.guide import search as search_mod
from channelguide.cache import client
import operator

def login(connection, id):
    try:
        user = User.query(id=id).get(connection)
    except LookupError:
        return None
    return user

def get_channel(connection, id):
    return Channel.get(connection, id, join=['categories', 'tags', 'items',
                                             'owner', 'language','rating'],
                       load=['subscription_count_today',
                             'subscription_count_month',
                             'subscription_count'])

def get_channel_by_url(connection, url):
    return Channel.query(url=url).join('categories', 'tags',
                                       'items', 'owner',
                                       'language').get(
        connection)

def get_channels_query(connection, filter, value, sort=None, loads=None):
    query = Channel.query_approved()
    join = None
    if filter == 'category':
        try:
            category_id = Category.query(name=value).get(connection).id
        except LookupError:
            return []
        join = 'categories'
        query.join(join)
        query.joins[join].where(id=category_id)
    elif filter == 'tag':
        try:
            tag_id = Tag.query(name=value).get(connection).id
        except LookupError:
            return []
        join = 'tags'
        query.join(join)
        query.joins[join].where(id=tag_id)
    elif filter == 'language':
        try:
            language_id = Language.query(name=value).get(connection).id
        except LookupError:
            return []
        query.where(Channel.c.primary_language_id == language_id)
    elif filter == 'featured':
        if value:
            query.where(Channel.c.featured)
        else:
            query.where(Channel.c.featured.negate())
    elif filter == 'hd':
        if value:
            query.where(Channel.c.hi_def)
        else:
            query.where(Channel.c.hi_def.negate())
    elif filter == 'feed':
        if value:
            query.where(Channel.c.url.is_not(None))
        else:
            query.where(Channel.c.url.is_(None))
    elif filter == 'name':
        if value:
            query.where(Channel.c.name.like(value + '%'))
    elif filter == 'search':
        query = search_mod.search_channels(value.split())
    else:
        raise ValueError('unknown filter: %r' % (filter,))
    if sort is not None and sort[0] == '-':
        desc = True
        sort = sort[1:]
    else:
        desc = False
    if not sort:
        sort = 'name' # default to sorting by name
    if sort in ('name', 'id'):
        query.order_by(getattr(Channel.c, sort), desc=desc)
    elif sort == 'age':
        query.order_by(Channel.c.approved_at, desc=desc)
    elif sort == 'popular':
        query.load('subscription_count_month')
        query.order_by('subscription_count_month', desc=desc)
    elif sort.startswith('rating'):
        query.join('rating')
        query.where(query.joins['rating'].c.count > 3)
        if sort == 'ratingcount':
            return query.count(connection)
        query.order_by(query.joins['rating'].c.average, desc=desc)
    elif sort == 'count':
        return query.count(connection)
    else:
        raise ValueError('unknown sort type: %r' % sort)
    return query

def _split_loads(loads):
    if loads:
        joins = [name for name in loads if not getattr(Channel.c, name, False)]
        loads = [name for name in loads if getattr(Channel.c, name, False)]
    else:
        joins = loads = ()
    return joins, loads

def _add_limit_and_offset(query, limit, offset):
    if limit is None:
        limit = 20
    if limit > 100:
        limit = 100
    if offset is None or offset < 0:
        offset = 0
    return query.limit(limit).offset(offset)

def get_feeds(connection, filter, value, sort=None, limit=None, offset=None,
              loads=None):
    query = get_channels_query(connection, filter, value, sort=sort)
    if isinstance(query, long):
        return query
    _add_limit_and_offset(query, limit, offset)
    query.where(Channel.c.url.is_not(None))
    joins, loads = _split_loads(loads)
    query.load(*loads)
    results = query.execute(connection)
    if results:
        results.join(*joins).execute(connection)
    return results

def get_shows(connection, filter, value, sort=None, limit=None, offset=None,
              loads=None):
    query = get_channels_query(connection, filter, value, sort=sort)
    if isinstance(query, long):
        return query
    _add_limit_and_offset(query, limit, offset)
    query.where(Channel.c.url.is_(None))
    joins, loads = _split_loads(loads)
    query.load(*loads)
    results = query.execute(connection)
    if results:
        results.join(*joins).execute(connection)
    return results

def get_channels(connection, filter, value, sort=None, limit=None, offset=None,
                 loads=None):
    """
    The old API method which returns a list of channels.  With the redesign and
    the inclusion of sites, you should use either get_feeds or get_sites.
    """
    query = get_channels_query(connection, filter, value, sort=sort)
    if isinstance(query, long):
        return query
    _add_limit_and_offset(query, limit, offset)
    joins, loads = _split_loads(loads)
    query.load(*loads)
    results = query.execute(connection)
    if results:
        results.join(*joins).execute(connection)
    return results

def search(connection, terms):
    query = search_mod.search_channels(terms)
    return query.execute(connection)

def get_rating(connection, user, channel):
    try:
        r = Rating.query(user_id=user.id, channel_id=channel.id).get(
            connection)
    except LookupError:
        return
    else:
        return r.rating

def get_ratings(connection, user, rating=None):
    if rating is None:
        return dict((r.channel, r.rating) for r in
                    Rating.query(user_id=user.id).join('channel').execute(
                connection))
    else:
        return [r.channel for r in
                Rating.query(user_id=user.id, rating=rating).join(
                'channel').execute(connection)]

def get_recommendations(connection, user, start=0, length=10):
    rating_query = Rating.query(user_id=user.id).order_by(Rating.c.timestamp)
    ratings = rating_query.execute(connection)
    added_query = AddedChannel.query(user_id=user.id).order_by(
        AddedChannel.c.timestamp)
    added_channels = added_query.execute(connection)
    if ratings:
        if added_channels:
            key = str(
                max(ratings[-1].timestamp,
                    added_channels[-1].timestamp).isoformat())
        else:
            key = str(ratings[-1].timestamp.isoformat())
        cacheKey = ':'.join(('recommendations_for', str(user.id),
                             key))
        result = client.get(cacheKey)
        if result is None:
            (estimatedRatings,
             reasons) = recommendations.get_recommendations_from_ratings(
                connection, ratings)
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
            client.set(cacheKey, result)
        else:
            estimatedRatings, reasons, ids = result
        if start is None:
            return len(ids)
        if not ids:
            return []
        query = Channel.query(Channel.c.id.in_(ids))
        query.join('rating')
        channels = list(query.execute(connection))
        for channel in channels:
            channel.guessed = estimatedRatings[channel.id]
            if channel.id in reasons:
                channelReasons = dict((cid, score) for (score, cid) in
                                      reasons[channel.id][-3:])
                query = Channel.query(Channel.c.id.in_(channelReasons.keys()))
                channel.reasons = list(query.execute(connection))
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

def list_labels(connection, type):
    if type == 'category':
        model = Category
    elif type == 'language':
        model = Language
    else:
        raise ValueError("type must be 'category' or 'language'")
    return model.query().order_by(model.c.name).execute(connection)
