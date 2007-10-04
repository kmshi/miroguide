import time, datetime, heapq
from channelguide.cache import client
from channelguide.guide.tables import channel_subscription
from sqlhelper.orm.query import ResultHandler
def timing(f):
    def inner(*args, **kw):
        t = time.time()
        ret = f(*args, **kw)
        u = time.time()
        fi = file('/tmp/getpopular', 'a')
        fi.write('%r %r %f\n' % (args, kw, u-t))
        fi.close()
        return ret
    return inner

def _cache_key(id, name, cached = {}):
    """
    Get the cache key for a channel count.
    """
    if (id, name) in cached:
        return cached[(id, name)]
    if name is None:
        val = 'Count:%i' % id
    else:
        now = int(time.time())
        if name == 'today':
            now /= 300 # every 5 minutes
        elif name == 'month':
            now /= 3600 # every hour
        val = 'Count:%i:%s:%i' % (id, name, now)
    cached[(id, name)] = val
    return val

def get_popular(name, connection, limit=None, query=None, use_cache=True):
    return _simple_get_popular(name, connection, limit, query, use_cache)
    if query is None:
        # have to do this late, otherwise it's a circular dependency
        from channelguide.guide.models import Channel
        query = Channel.query_approved()
        if use_cache:
            query.cacheable = client
            query.cacheable_time = 300
    select = query.make_select()
    results = select.execute(connection)
    keys = [_cache_key(r[0], name) for r in results]
    if use_cache:
        ret = client.get_multi(keys)
    else:
        ret = {} # refresh the cache
    if len(keys) != len(ret): # some keys are missing
        missing_ids = [int(key.split(':')[1])
                for key in keys if key not in ret]
        for (id, count) in _get_missing_values(missing_ids, connection, name):
            key = _cache_key(id, name)
            client.set(key, count)
            ret[key] = count
    # now ret contains all the count values
    results = [(ret[_cache_key(r[0], name)], r) for r in results]
    if limit:
        if isinstance(limit, (list, tuple)): #slice
            start, end = limit[0], limit[0] + limit[1]
        else: # top n
            start, end = 0, limit
        results = heapq.nlargest(end, results)
        if start:
            results = results[start:]
    else:
        results.sort()
        results.reverse()
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
    now = datetime.datetime.now()
    if (now - timestamp) < datetime.timedelta(days=31):
        _increment_or_load(id, 'month', connection)
        if (now - timestamp) < datetime.timedelta(days=1):
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

def _simple_get_popular(name, connection, limit, query, use_cache):
    if name is None:
        load = 'subscription_count'
        cachetime = 24*60*60
    else:
        if name == 'today':
            cachetime = 5 * 60
        else:
            cachetime = 60*60
        load = 'subscription_count_' + name
    if query is None:
        from channelguide.guide.models import Channel
        query = Channel.query_approved()
    query.load(load)
    query.order_by(query.get_column(load), desc=True)
    if limit:
        try:
            len(limit)
        except:
            query.limit(limit)
        else:
            query.offset(limit[0])
            query.limit(limit[1])
    if use_cache:
        query.cacheable = client
        query.cacheable_time = cachetime
    return query.execute(connection)
