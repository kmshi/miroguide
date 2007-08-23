#!/usr/bin/env python2.5
from channelguide import manage, init # set up environment
import math
init.init_external_libraries()

from channelguide import db
from sqlhelper.orm.query import Query
from sqlhelper.sql.statement import Select
database = db.connect()

def getAllSimilar(channel):
    sql = """SELECT DISTINCT channel_id FROM cg_channel_subscription WHERE
(channel_id<>%s AND ip_address IN (
SELECT ip_address FROM cg_channel_subscription WHERE ip_address!="0.0.0.0" AND
    channel_id=%s))"""
    results = database.execute(sql, (channel, channel))
    return [e[0] for e in results]

def getSimilarity(channel1, channel2):
    channel1 = int(channel1)
    channel2 = int(channel2)
    sql = 'SELECT channel_id, ip_address from cg_channel_subscription WHERE channel_id=%s OR channel_id=%s ORDER BY ip_address'
    entries = database.execute(sql, (channel1, channel2))
    if not entries:
        return 0.0
    vectors = {}
    for (channel, ip) in entries:
        vectors.setdefault(ip, [False, False])
        i = int(channel)
        if i == channel1:
            vectors[ip][0] = True
        elif i == channel2:
            vectors[ip][1] = True
        else:
            raise RuntimeError("%r != to %r or %r" % (channel, channel1, channel2))
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

def main():
    hit = set()
    database.execute("DELETE FROM cg_channel_recommendations");
    channels = [e[0] for e in channel.select('id').execute(database)]
    for c1 in channels:
        gas = getAllSimilar(c1)
        if gas:
            for c2 in gas:
                if c1 > c2:
                    c1, c2 = c2, c1
                k = (c1, c2)
                if k not in hit:
                    hit.add(k)
                    gs = getSimilarity(c1, c2)
                    if gs:
                        database.execute("INSERT INTO cg_channel_recommendations VALUES (%s, %s, %s)", (c1, c2, gs))
                        database.commit()
                        print c1, c2, gs
if __name__ == "__main__":
    main()
