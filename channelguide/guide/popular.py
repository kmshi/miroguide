from datetime import date
from channelguide.cache import client
from channelguide.guide.tables import channel_subscription

def _cache_key(id, name):
    """
    Get the cache key for a channel count.
    """
    if name == 'today':
        today = date.today()
        return 'Count:%i:%i:%i:%i' % (id, today.year, today.month, today.day)
    elif name =='month':
        today = date.today()
        return 'Count:%i:%i:%i' % (id, today.year, today.month)
    else:
        return 'Count:%i' % id

def get_popular(name, connection, limit=None, query=None):
    if query is None:
        # have to do this late, otherwise it's a circular dependency
        from channelguide.guide.models import Channel
        query = Channel.query_approved()
    channels = query.execute(connection)
    keys = [_cache_key(c.id, name) for c in channels]
    ret = client.get_multi(keys)
    if len(keys) != len(ret): # some keys are missing
        missing_ids = [int(key.split(':')[1])
                for key in keys if key not in ret]
        for (id, count) in _get_missing_values(missing_ids, connection, name):
            key = _cache_key(id, name)
            client.set(key, count)
            ret[key] = count
    # now ret contains all the count values
    channels = list(channels)
    if len(channels) > 1:
        channels.sort(_return_sort_and_add(name, ret))
    else:
        value = ret[_cache_key(channels[0].id, name)]
        if name is None:
            attr = 'subscription_count'
        else:
            attr = 'subscription_count_' + name
        setattr(channels[0], attr, value)
    if limit:
        if isinstance(limit, (list, tuple)): #slice
            return channels[limit[0]:limit[0]+limit[1]]
        else: # top
            return channels[:limit]
    return channels

def _get_missing_values(missing_ids, connection, name):
    sql = """SELECT id, (SELECT COUNT(*) FROM cg_channel_subscription
WHERE channel_id=id"""
    if name is not None:
        if name == 'today':
            timeline = 'DAY'
        elif name == 'month':
            timeline = 'MONTH'
        interval = 'DATE_SUB(NOW(), INTERVAL 1 %s)' % timeline
        sql += ' AND cg_channel_subscription.timestamp > %s' % interval
    if len(missing_ids) == 1:
        sql += ') FROM cg_channel WHERE id=%s'
        args = missing_ids
    else:
        sql += ") FROM cg_channel WHERE id IN %s"
        args = (missing_ids,)
    return connection.execute(sql, args)

def _return_sort_and_add(name, keys):
    if name is None:
        attr = 'subscription_count'
    else:
        attr = 'subscription_count_' + name
    def set(channel):
        value = keys[_cache_key(channel.id, name)]
        setattr(channel, attr, value)
        return value
    def sorter(c1, c2):
        count1 = set(c1)
        count2 = set(c2)
        return cmp(count2, count1) # descending order
    return sorter

def add_subscription(id, connection, timestamp):
    _increment_or_load(id, None, connection)
    today = date.today()
    if timestamp.year == today.year and timestamp.month == today.month:
        _increment_or_load(id, 'month', connection)
        if timestamp.day == today.day:
            _increment_or_load(id, 'today', connection)

def _increment_or_load(id, name, connection):
    key = _cache_key(id, name)
    try:
        i = client.incr(key)
        if i is not None:
            # memcached will happily increment something that's expired
            # so, we check to see if it's really there
            if client.get(key) == i:
                return
    except ValueError, e:
        # memcached sometimes raises this from incr instead of returning None
        pass
    ((id, value),) = _get_missing_values([id], connection, name)
    client.set(key, value)
