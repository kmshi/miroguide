# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from channelguide.guide import tables
from channelguide.guide.models import Channel, Rating
import logging
import math

def get_recommendations_from_ratings(connection, ratings):
    ratings = dict((r.channel_id, r.rating) for r in ratings)
    recommendations = _get_recommendations(connection, ratings.keys())
    scores, numScores, topThree = _calculate_scores(recommendations,
            ratings)
    return _filter_scores(connection, scores, numScores), topThree

def _get_recommendations(connection, ids):
    if not ids:
        return []
    table = tables.channel_recommendations
    select = table.select()
    for column in table.c:
        select.columns.append(column)
    select.wheres.append(
            (table.c.channel1_id.in_(ids)) |
            (table.c.channel2_id.in_(ids)))
    return select.execute(connection)

def _filter_scores(connection, scores, numScores):
    valid = [id for id in numScores if numScores[id] > 3]
    if not valid:
        return scores
    query = Channel.query(Channel.c.id.in_(valid), state=Channel.APPROVED,
                                      archived=0)
    channels = query.execute(connection)
    return dict((c.id, scores[c.id]) for c in channels)

def _calculate_scores(recommendations, ratings):
    simTable = {}
    scores = {}
    topThree = {}
    numScores = {}
    totalSim = {}
    for channel1_id, channel2_id, cosine in recommendations:
        if channel1_id in ratings:
            simTable.setdefault(channel1_id, {})[channel2_id] = cosine
        if channel2_id in ratings:
            simTable.setdefault(channel2_id, {})[channel1_id] = cosine
    for channel1_id in simTable:
        rating = ratings.get(channel1_id)
        if rating is None:
            continue
        for channel2_id, cosine in simTable[channel1_id].items():
            if channel2_id in ratings:
                continue
            scores.setdefault(channel2_id, 0)
            totalSim.setdefault(channel2_id, 0)
            numScores.setdefault(channel2_id, 0)
            score = (cosine * (rating-2.5))
            scores[channel2_id] += score
            totalSim[channel2_id] += abs(cosine)
            numScores[channel2_id] += 1
            if rating > 2:
                topThree.setdefault(channel2_id, [])
                thisTop = topThree[channel2_id]
                thisTop.append((score, channel1_id))
                thisTop.sort()
    scores = dict((id, (scores[id] / totalSim[id]) + 2.5) for id in scores)
    return scores, numScores, topThree

def recalculate_similarity_recent(connection):
    seconds = 60*60*24
    #subscribed = set(get_recently_subscribed(connection, seconds))
    channels = set(get_recently_rated(connection, seconds))
    #channels = subscribed | rated
    if not channels:
        return
    recalculate_similarity(channels, connection)

def recalculate_similarity(channels, connection):
    logging.info('calculating similarity for %i channels' % len(channels))
    for c1 in channels:
        logging.info('deleting similar for %s' % c1)
        delete_all_similarities(c1, connection)
        logging.info('finding similar for %s' % c1)
        similar = find_relevant_similar(c1, connection)
        if similar:
            for c2 in similar:
                id1 = c1.id
                id2 = c2
                if id1 > id2:
                    id1, id2 = id2, id1
                k = (id1, id2)
                logging.info('calculating similarity for %i & %i' % k)
                gs = get_similarity(c1, connection, c2)
                if gs:
                    i = tables.channel_recommendations.insert()
                    i.add_values(channel1_id=id1,
                                 channel2_id=id2,
                                 cosine=gs)
                    i.execute(connection)
        logging.info('commiting')
        connection.commit()

def get_recently_subscribed(connection, seconds):
    sql = """SELECT DISTINCT channel_id FROM cg_channel_subscription JOIN cg_channel ON cg_channel_subscription.channel_id = cg_channel.id WHERE (NOW()-timestamp) < %s AND ip_address!=%s AND ignore_for_recommendations<>%s AND state=%s"""
    args = (seconds, '0.0.0.0', True, 'A')
    results = connection.execute(sql, args)
    query = Channel.query()
    query.where(Channel.c.id.in_([e[0] for e in results]))
    return query.execute(connection)

def get_recently_rated(connection, seconds):
    sql = """SELECT DISTINCT channel_id FROM cg_channel_rating JOIN cg_channel ON cg_channel_rating.channel_id = cg_channel.id WHERE (NOW()-timestamp) < %s AND state=%s"""
    args = (seconds, 'A')
    results = connection.execute(sql, args)
    query = Channel.query().join('categories')
    query.where(Channel.c.id.in_([e[0] for e in results]))
    return query.execute(connection)

def insert_similarity(channel, connection, other):
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

def delete_all_similarities(channel, connection):
    delete = tables.channel_recommendations.delete()
    delete.wheres.append(
            (tables.channel_recommendations.c.channel1_id==channel.id) |
            (tables.channel_recommendations.c.channel2_id==channel.id))
    delete.execute(connection)

def delete_similarity(channel, connection, other):
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

def find_relevant_similar(channel, connection):
    #return set(
           # find_relevant_similar_subscription(channel, connection)) |
    return       set(
                    find_relevant_similar_rating(channel, connection))

def find_relevant_similar_subscription(channel, connection, ip_address=None):
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

def find_relevant_similar_rating(channel, connection):
    ratings = Rating.query(channel_id=channel.id).execute(connection)
    if not ratings:
        return []
    user_ids = [r.user_id for r in ratings]
    query = Rating.query(Rating.c.user_id.in_(user_ids))
    query.where(Rating.c.channel_id != channel.id)
    return set([c.channel_id for c in query.execute(connection)])

def get_similarity(channel, connection, other):
    """
    Returns the similarity between two channels.  channel is a Channel object;
    other is a channel id.
    """
    #from_sub = get_similarity_from_subscriptions(channel, connection, other)
    from_rat = get_similarity_from_ratings(channel, connection, other)
    from_lang = get_similarity_from_languages(channel, connection, other)
    from_cat = get_similarity_from_categories(channel, connection, other)

    return sum((from_rat * 6, from_lang * 3, from_cat)) / 10

def get_similarity_from_subscriptions(channel, connection, other):
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
    c = cosine(v1, v2)
    return c

def get_similarity_from_ratings(channel, connection, other):
    query = Rating.query().where(Rating.c.channel_id.in_((channel.id, other)))
    vectors = {}
    for rating in query.execute(connection):
        vectors.setdefault(rating.user_id, [None, None])
        i = int(rating.channel_id)
        if not rating.rating:
            continue
        if i == channel.id:
            vectors[rating.user_id][0] = rating.rating
        else:
            vectors[rating.user_id][1] = rating.rating
    keys = [key for key in vectors.keys() if None not in vectors[key]]
    keys.sort()
    v1 = [vectors[k][0] for k in keys]
    v2 = [vectors[k][1] for k in keys]
    pc = pearson_coefficient(v1, v2)
    if len(v1) < 5:
        pc /= 2
    return pc

def get_similarity_from_categories(channel, connection, other):
    cat1 = set([cat.id for cat in channel.categories])
    cat2 = set([cat.id for cat in Channel.query(id=other
                                                       ).join('categories'
                                                              ).get(
        connection).categories])
    if not len(cat1 | cat2):
        return 0.0
    return float(len(cat1 & cat2)) / len(cat1 | cat2)

def get_similarity_from_languages(channel, connection, other):
    lang1 = set([channel.primary_language_id])

    other_c = Channel.query(id=other).get(connection)
    lang2 = set([other_c.primary_language_id])
    if not len(lang1 | lang2):
        return 0.0
    return float(len(lang1 & lang2)) / len(lang1 | lang2)

def pearson_coefficient(vector1, vector2):
    n = float(len(vector1))
    if n < 3: # two points always have a linear corelation
        return 0.0
    sum1 = sum(vector1)
    sum2 = sum(vector2)
    sq1 = sum([v**2 for v in vector1])
    sq2 = sum([v**2 for v in vector2])
    dp = dotProduct(vector1, vector2)
    numerator = dp - (sum1*sum2/n)
    denominator = math.sqrt((sq1 - sum1**2 / n) * (sq2 - sum2**2 / n))
    if denominator == 0:
        return 0.0
    else:
        return numerator / denominator

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

