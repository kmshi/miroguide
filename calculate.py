#!/usr/bin/env python2.5
from channelguide import manage, init # set up environment
import math, sys
init.init_external_libraries()

from channelguide import db
from channelguide.guide.tables import channel
from channelguide.guide.models.channel import Channel
from sqlhelper.orm.query import Query
from sqlhelper.sql.statement import Select
database = db.connect()

def getAllSimilar(channel):
    sql = """SELECT DISTINCT channel_id FROM cg_channel_subscription WHERE
(channel_id<>%s AND ip_address IN (
SELECT ip_address FROM cg_channel_subscription JOIN cg_channel ON cg_channel_subscription.channel_id=cg_channel.id WHERE ip_address!=%s AND
    channel_id=%s AND (NOW()-timestamp) < %s AND ignore_for_recommendations<>%s AND state=%s))"""
    results = database.execute(sql, (channel, "0.0.0.0", channel, 16070400, False, 'A'))
    return [e[0] for e in results]

def getRecent(seconds):
    sql = """SELECT DISTINCT channel_id FROM cg_channel_subscription JOIN cg_channel ON cg_channel_subscription.channel_id = cg_channel.id WHERE (NOW()-timestamp) < %s AND ip_address!=%s AND ignore_for_recommendations<>%s AND state=%s"""
    results = database.execute(sql, (seconds, "0.0.0.0", False, 'A'))
    return [e[0] for e in results]

def getSimilarity(channel1, channel2):
    c = Channel()
    c.id = channel1
    return c.get_similarity(database, channel2)

def calculateAll():
    database.execute("DELETE FROM cg_channel_recommendations");
    channels = [e[0] for e in channel.select('id').execute(database)]
    calculateRecommendations(channels)

def calculateTwoDays():
    channels = map(int, getRecent(60*60*24*2))
    container = ','.join([str(x) for x in channels])
    database.execute("DELETE FROM cg_channel_recommendations WHERE channel1_id IN (%s) OR channel2_id IN (%s)" % (container, container))
    calculateRecommendations(channels)

def calculateRecommendations(channels):
    hit = set()
    for c1 in channels:
        gas = getAllSimilar(c1)
        if gas:
            for c2 in gas:
                id1 = c1
                id2 = c2
                if id1 > id2:
                    id1, id2 = id2, id1
                k = (id1, id2)
                if k not in hit:
                    hit.add(k)
                    gs = getSimilarity(c1, c2)
                    if gs:
                        database.execute("INSERT LOW_PRIORITY INTO cg_channel_recommendations VALUES (%s, %s, %s)", (id1, id2, gs))
            database.commit()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'all':
        calculateAll()
    else:
        calculateTwoDays()
