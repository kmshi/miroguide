from channelguide.q import *
from channelguide.guide import recommendations
import math

g1 = []
g2 = []
channels = set()

for user in  User.query().join('channel_rating').execute(connection):
    if len(user.channel_rating):
        if user.id % 2:
            g1.append(user)
        else:
            if len(user.channel_rating) > 6:
                g2.append(user)
                user.channel_rating.join('channel').execute(connection)
                for rating in user.channel_rating[:len(user.channel_rating)/2]:
                    channel = rating.channel
                    if channel not in channels:
                        channel.join('categories',
                                     'secondary_languages').execute(connection)
                        channels.add(channel)

print len(g1)
print len(g2)
print len(channels)
# g1 is the test group
# g2 is the verification group

g1_ids = [u.id for u in g1]

def find_relevant_similar_rating(channel, connection):
    print 'finding relevant', channel.id
    ratings = Rating.query(channel_id=channel.id).execute(connection)
    if not ratings:
        return []
    user_ids = [r.user_id for r in ratings if r.user_id in g1_ids]
    if not user_ids:
        return []
    query = Rating.query(Rating.c.user_id.in_(user_ids))
    query.where(Rating.c.channel_id != channel.id)
    return set([c.channel_id for c in query.execute(connection)])

def get_similarity_from_ratings(channel, connection, other):
    query = Rating.query().where(Rating.c.channel_id.in_((channel.id, other)))
    query.where(Rating.c.user_id.in_(g1_ids))
    vectors = {}
    for rating in query.execute(connection):
        vectors.setdefault(rating.user_id, [None, None])
        i = int(rating.channel_id)
        if i == channel.id:
            vectors[rating.user_id][0] = rating.rating
        else:
            vectors[rating.user_id][1] = rating.rating
    keys = [key for key in vectors.keys() if None not in vectors[key]]
    keys.sort()
    v1 = [vectors[k][0] for k in keys]
    v2 = [vectors[k][1] for k in keys]
    return recommendations.pearson_coefficient(v1, v2)

recommendations.find_relevant_similar_rating = find_relevant_similar_rating
recommendations.get_similarity_from_ratings = get_similarity_from_ratings

recommendations.recalculate_similarity(
    sorted(channels,
           key=lambda c: c.id), connection)

errors = []

for user in g2:
    first = user.channel_rating[:len(user.channel_rating) / 2]
    second = user.channel_rating[len(user.channel_rating) / 2:]
    ratings = dict((r.channel_id, r.rating) for r in first)
    recs = recommendations._get_recommendations(connection,
                                                          ratings.keys())
    scores, numScores, topThree = recommendations._calculate_scores(
        recs, ratings)
    for rating in second:
        if rating.channel_id not in scores:
            continue
        r = rating.rating
        if r is None:
            continue
        error = r - scores[rating.channel_id]
        errors.append(error ** 2)

avg = sum(errors) / len(errors)
print 'RMSE', math.sqrt(avg)
