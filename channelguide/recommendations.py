#!/usr/bin/env python2.5
import math, sys, logging, time
from channelguide.guide.tables import channel
from channelguide.guide.models.channel import Channel
from sqlhelper.orm.query import Query
from sqlhelper.sql.statement import Select

def getAllSimilar(database, channel):
    sql = """SELECT c1.channel_id, COUNT(c2.ip_address) AS sim_count
    FROM cg_channel_subscription AS c1
    JOIN cg_channel ON cg_channel.id=c1.channel_id
    JOIN cg_channel_subscription AS c2 ON
        c1.ip_address=c2.ip_address AND c2.channel_id=%s
        AND c2.timestamp > DATE_SUB(NOW(), INTERVAL 1 MONTH)
        AND c2.ignore_for_recommendations=%s
    WHERE c1.channel_id<>%s
        AND c1.timestamp > DATE_SUB(NOW(), INTERVAL 1 MONTH)
        AND c1.ignore_for_recommendations=%s
        AND c1.ip_address<>%s AND state=%s
    GROUP BY c1.channel_id ORDER BY sim_count DESC LIMIT 50;"""
    args = (channel, 0, channel, 0, "0.0.0.0", 'A')
    return [e[0] for e in database.execute(sql, args)]
#    c = Channel()
#    c.id = channel
#    return c.find_relevant_similar(database)

def getRecent(database, seconds):
    sql = """SELECT DISTINCT channel_id FROM cg_channel_subscription JOIN cg_channel ON cg_channel_subscription.channel_id = cg_channel.id WHERE (NOW()-timestamp) < %s AND ip_address!=%s AND ignore_for_recommendations<>%s AND state=%s"""
    args = (seconds, '0.0.0.0', True, 'A')
    results = database.execute(sql, args)
    return [e[0] for e in results]

def getSimilarity(database, channel1, channel2, entries=None):
    c = Channel()
    c.id = channel1
    return c.get_similarity(database, channel2)

def calculateAll(database):
    database.execute("DELETE FROM cg_channel_recommendations")
    query = channel.select('id')
    query.wheres.append(channel.c.state=='A')
    channels = [e[0] for e in query.execute(database)]
    calculateRecommendations(database, channels)

def timeit(f, *args):
    s = time.time()
    r = f(*args)
    print f,time.time()-s
    return r

def calculateRecent(database, length=None):
    if length is None:
        length = 60*60*24 # 1 day
    channels = map(int, getRecent(database, length))
    if not channels:
        return
    container = ','.join([str(x) for x in channels])
    database.execute("DELETE FROM cg_channel_recommendations WHERE channel1_id IN (%s) OR channel2_id IN (%s)" % (container, container))
    logging.info('calculating for %i channels' % len(channels))
    calculateRecommendations(database, channels)

def calculateRecommendations(database, channels):
    hit = set()
    inserts = []
    for c1 in channels:
        gas = getAllSimilar(database, c1)
#        logging.info('%i has %i similar' % (c1, len(gas)))
        if gas:
            for c2 in gas:
                id1 = c1
                id2 = c2
                if id1 > id2:
                    id1, id2 = id2, id1
                k = (id1, id2)
                if k not in hit:
                    hit.add(k)
                    gs = getSimilarity(database, c1, c2)
                    if gs:
                        database.execute("INSERT LOW_PRIORITY INTO cg_channel_recommendations VALUES (%s, %s, %s)", (id1, id2, gs))
    database.commit()

if __name__ == "__main__":
    from channelguide import manage, init # set up environment
    init.init_external_libraries()

    from channelguide import db
    database = db.connect()
    if len(sys.argv) > 1 and sys.argv[1] == 'all':
        calculateAll(database)
    else:
        calculateTwoDays(database)
