# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

import math
from datetime import datetime, timedelta

from channelguide.channels.models import Channel
from channelguide.ratings.models import Rating
from channelguide.subscriptions.models import Subscription

def filter_scores(scores, numScores):
    valid = [id for id in numScores if numScores[id] > 3]
    if not valid:
        return scores
    channels = Channel.objects.approved().filter(pk__in=valid,
                                              archived=0)
    return dict((c.id, scores[c.id]) for c in channels)

def calculate_scores(recommendations, ratings):
    simTable = {}
    scores = {}
    topThree = {}
    numScores = {}
    totalSim = {}
    for similarity in recommendations:
        channel1_id, channel2_id, cosine = \
            similarity.channel1_id, similarity.channel2_id, similarity.cosine
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



def find_relevant_similar(channel):
    #return set(
           # find_relevant_similar_subscription(channel, connection)) |
    return       set(
                    find_relevant_similar_rating(channel))

def find_relevant_similar_subscription(channel, ip_address=None):
    """
    Returns a list of integers representing channel ids.
    """
    query = Subscription.objects.filter(
        channel__state=Channel.APPROVED,
        timestamp__gt=(datetime.now()-timedelta(days=31)),
        ignore_for_recommendations=False).exclude(
        ip_address='0.0.0.0').exclude(
        channel=channel)
    if ip_address is None:
        query = query.filter(
            ip_address__in=Subscription.objects.filter(
                channel=channel,
                timestamp__gt=(datetime.now()-timedelta(days=31)),
                ignore_for_recommendations=False).exclude(
                ip_address='0.0.0.0').values_list('ip_address',
                                             flat=True).distinct())
    else:
        query = query.filter(ip_address=ip_address)

    return query.values_list('channel', flat=True).distinct()

def find_relevant_similar_rating(channel):
    ratings = Rating.objects.filter(channel=channel)
    if not ratings.count():
        return []
    return Rating.objects.filter(
        user__in=ratings.values_list('user', flat=True).distinct()).exclude(
        channel=channel).values_list('channel', flat=True).distinct()

def get_similarity(channel, other):
    """
    Returns the similarity between two channels.  channel and other are Channel
    objects.
    """
    #from_sub = get_similarity_from_subscriptions(channel, other)
    from_rat = get_similarity_from_ratings(channel, other)
    from_lang = get_similarity_from_languages(channel, other)
    from_cat = get_similarity_from_categories(channel, other)
    return sum((from_rat * 6, from_lang * 3, from_cat)) / 10

def get_similarity_from_subscriptions(channel, other):
    entries = Subscription.objects.filter(
        channel__in=[channel, other],
        timestamp__gt=(datetime.now()-timedelta(days=31)),
        ignore_for_recommendations=False).exclude(
        ip_address='0.0.0.0')
    if not entries:
        return 0.0
    vectors = {}
    for subscription in entries:
        vectors.setdefault(subscription.ip_address, [False, False])
        i = subscription.channel_id
        if i == channel.id:
            vectors[subscription.ip_address][0] = True
        elif i == other.id:
            vectors[subscription.ip_address][1] = True
        else:
            raise RuntimeError("%r != to %r or %r" % (i, channel.id, other))
    keys = vectors.keys()
    keys.sort()
    v1 = [vectors[k][0] for k in keys]
    v2 = [vectors[k][1] for k in keys]
    c = cosine(v1, v2)
    return c

def get_similarity_from_ratings(channel, other):
    vectors = {}
    for rating in Rating.objects.filter(channel__in=[channel, other]):
        vectors.setdefault(rating.user, [None, None])
        i = int(rating.channel_id)
        if not rating.rating:
            continue
        if i == channel.id:
            vectors[rating.user][0] = rating.rating
        else:
            vectors[rating.user][1] = rating.rating
    keys = [key for key in vectors.keys() if None not in vectors[key]]
    keys.sort()
    v1 = [vectors[k][0] for k in keys]
    v2 = [vectors[k][1] for k in keys]
    pc = pearson_coefficient(v1, v2)
    if len(v1) < 5:
        pc /= 2
    return pc

def get_similarity_from_categories(channel, other):
    cat1 = set(channel.categories.all())
    cat2 = set(other.categories.all())
    if not len(cat1 | cat2):
        return 0.0
    return float(len(cat1 & cat2)) / len(cat1 | cat2)

def get_similarity_from_languages(channel, other):
    lang1 = set([channel.language])
    lang2 = set([other.language])
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

