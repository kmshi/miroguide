from channelguide.guide import tables
from channelguide.guide.models import Channel
import logging
import math

def recalculate_recently_subscribed(connection):
    channels = get_recently_subscribed(connection, 60*60*24)
    if not channels:
        return
    recalculate_recommendations(channels, connection)

def recalculate_recommendations(channels, connection):
    logging.info('calculating for %i channels' % len(channels))
    hit = set()
    inserts = []
    for c1 in channels:
        similar = find_relevant_similar(c1, connection)
        if similar:
            for c2 in similar:
                id1 = c1.id
                id2 = c2
                if id1 > id2:
                    id1, id2 = id2, id1
                k = (id1, id2)
                if k not in hit:
                    hit.add(k)
                    gs = get_similarity(c1, connection, c2)
                    if gs:
                        connection.execute("INSERT LOW_PRIORITY INTO cg_channel_recommendations VALUES (%s, %s, %s)", (id1, id2, gs))
            connection.commit()

def get_recently_subscribed(connection, seconds):
    sql = """SELECT DISTINCT channel_id FROM cg_channel_subscription JOIN cg_channel ON cg_channel_subscription.channel_id = cg_channel.id WHERE (NOW()-timestamp) < %s AND ip_address!=%s AND ignore_for_recommendations<>%s AND state=%s"""
    args = (seconds, '0.0.0.0', True, 'A')
    results = connection.execute(sql, args)
    query = Channel.query()
    query.where(Channel.c.id.in_([e[0] for e in results]))
    return query.execute(connection)

def recalculate_recommendations_for_ip(channel, connection, ip_address):
    if ip_address == '0.0.0.0':
        return # don't bother with no IP
    updates = find_relevant_similar(channel, connection, ip_address)
    for other in updates:
        delete_recommendation(channel, connection, other)
        insert_recommendation(channel, connection, other)

def insert_recommendation(channel, connection, other):
    recommendation = get_similarity(channel, connection, other)
    if recommendation == 0:
        return
    c1, c2 = channel.id, other
    if c1 > c2:
        c1, c2 = c2, c1
    insert = tables.channel_recommendations.insert()
    insert.add_values(channel1_id=c1, channel2_id=c2,
            cosine=recommendation)
    insert.execute(connection)

def delete_recommendation(channel, connection, other):
    c1 = channel.id
    c2 = other
    if c1 > c2:
        c1, c2 = c2, c1
    delete = tables.channel_recommendations.delete()
    delete.wheres.append(
            tables.channel_recommendations.c.channel1_id==c1)
    delete.wheres.append(
        tables.channel_recommendations.c.channel2_id==c2)
    delete.execute(connection)

def find_relevant_similar(channel, connection, ip_address=None):
    """
    Returns a list of integers representing channel ids.
    """
    ignoresWhere = """timestamp > DATE_SUB(NOW(), INTERVAL 1 MONTH)
AND ignore_for_recommendations=%s AND ip_address<>%s"""
    ignoresArgs = [False, '0.0.0.0']
    sql = """
SELECT DISTINCT channel_id FROM cg_channel_subscription
JOIN cg_channel ON cg_channel.id=channel_id
WHERE channel_id<>%%s AND %s AND cg_channel.state=%%s""" % ignoresWhere
    args = [channel.id] + ignoresArgs + ['A']
    if ip_address is None:
        sql += """ AND ip_address IN
(SELECT ip_address FROM cg_channel_subscription
WHERE channel_id=%%s AND %s)""" % ignoresWhere
        args.append(channel.id)
        args.extend(ignoresArgs)
    else:
        sql += " AND ip_address=%s"
        args.append(ip_address)
    results = connection.execute(sql, args)
    return [e[0] for e in results]

def get_similarity(channel, connection, other):
    sql = 'SELECT channel_id, ip_address from cg_channel_subscription WHERE channel_id IN (%s, %s) AND timestamp > DATE_SUB(NOW(), INTERVAL 1 MONTH) AND ip_address<>%s AND ignore_for_recommendations=%s ORDER BY ip_address'
    entries = connection.execute(sql, (channel.id, other, "0.0.0.0", False))
    if not entries:
        return 0.0
    vectors = {}
    for (i, ip) in entries:
        vectors.setdefault(ip, [False, False])
        i = int(i)
        if i == channel.id:
            vectors[ip][0] = True
        elif i == other:
            vectors[ip][1] = True
        else:
            raise RuntimeError("%r != to %r or %r" % (i, channel.id, other))
    keys = vectors.keys()
    keys.sort()
    v1 = [vectors[k][0] for k in keys]
    v2 = [vectors[k][1] for k in keys]
    return cosine(v1, v2)

def dotProduct(vector1, vector2):
    return sum([v1*v2 for v1, v2 in zip(vector1, vector2)])

def length(vector):
    return math.sqrt(sum([v**2 for v in vector]))

def cosine(v1, v2):
    l1 = length(v1)
    l2 = length(v2)
    if l1 == 0 or l2 == 0:
        return 0.0
    return dotProduct(v1, v2)/(l1 * l2)
