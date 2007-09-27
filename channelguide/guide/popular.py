from datetime import date
from channelguide.cache import client
from channelguide.guide.tables import channel_subscription
from sqlhelper.orm.query import ResultHandler
def _cache_key(id, name, cached = {}):
    """
    Get the cache key for a channel count.
    """
    if (id, name) in cached:
        return cached[(id, name)]
    if name == 'today':
        today = date.today()
        val = 'Count:%i:%i:%i:%i' % (id, today.year, today.month, today.day)
    elif name =='month':
        today = date.today()
        val = 'Count:%i:%i:%i' % (id, today.year, today.month)
    else:
        val = 'Count:%i' % id
    cached[(id, name)] = val
    return val

def get_popular(name, connection, limit=None, query=None):
    if query is None:
        # have to do this late, otherwise it's a circular dependency
        from channelguide.guide.models import Channel
        query = Channel.query_approved()
        query.cacheable = client
        query.cacheable_time = 300
    select = query.make_select()
    results = select.execute(connection)
    keys = [_cache_key(r[0], name) for r in results]
    ret = client.get_multi(keys)
    if len(keys) != len(ret): # some keys are missing
        missing_ids = [int(key.split(':')[1])
                for key in keys if key not in ret]
        for (id, count) in _get_missing_values(missing_ids, connection, name):
            key = _cache_key(id, name)
            client.set(key, count)
            ret[key] = count
    # now ret contains all the count values
    results = [(ret[_cache_key(r[0], name)], r) for r in results]
    results.sort()
    results.reverse()
    if limit:
        if isinstance(limit, (list, tuple)): #slice
            results = results[limit[0]:limit[0]+limit[1]]
        else: # top n
            results = results[:limit]
    if name is None:
        attr = 'subscription_count'
    else:
        attr = 'subscription_count_' + name
    handler = ResultHandler(query)
    for value, row in results:
        channel = handler.handle_data(iter(row))
        setattr(channel, attr, value)
    return handler.make_results()

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

def _return_sorter(name, ret):
    def sorter(c1, c2):
        count1 = ret[_cache_key(c1[0], name)]
        count2 = ret[_cache_key(c2[0], name)]
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
