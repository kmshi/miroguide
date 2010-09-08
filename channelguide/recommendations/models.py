from datetime import datetime, timedelta

from django.db import models

from channelguide.channels.models import Channel
from channelguide.ratings.models import Rating

from channelguide.recommendations import utils

class SimilarityManager(models.Manager):

    def calculate(self, channel1, channel2):
        if channel2.pk < channel1.pk:
            # channel1 always has the lower id
            channel1, channel2 = channel2, channel1
        try:
            similarity = self.get(channel1=channel1,
                                  channel2=channel2)
        except self.model.DoesNotExist:
            similarity = self.create(
                channel1=channel1,
                channel2=channel2,
                cosine = utils.get_similarity(channel1, channel2))

        return similarity.cosine

    def recalculate_all(self):
        self.all().delete()
        for channel1 in Channel.objects.approved():
            for channel2 in utils.find_relevant_similar(channel1):
                self.calculate(channel1, channel2)

    def recalculate_recent(self):
        for channel1_id in Rating.objects.filter(
            timestamp__gt=(datetime.now()-timedelta(days=1)),
            channel__state=Channel.APPROVED).values_list('channel',
                                                         flat=True).distinct():
            channel1 = Channel.objects.get(pk=channel1_id)
            for channel2_id in utils.find_relevant_similar(channel1):
                channel2 = Channel.objects.get(pk=channel2_id)
                self.filter(channel1=channel1,
                                          channel2=channel2).delete()
                self.filter(channel1=channel2,
                                          channel2=channel1).delete()
                self.calculate(channel1, channel2)

    def recommend_from_ratings(self, ratings):
        ratings_dict = dict((r.channel_id, r.rating) for r in ratings)
        recommendations = self.filter(
            models.Q(channel1__in=ratings_dict.keys()) |
            models.Q(channel2__in=ratings_dict.keys()))
        scores, numScores, topThree = utils.calculate_scores(recommendations,
                                                             ratings_dict)
        return utils.filter_scores(scores, numScores), topThree

class Similarity(models.Model):
    channel1 = models.ForeignKey('channels.Channel')
    channel2 = models.ForeignKey('channels.Channel',
                                 related_name='similarity2_set')
    cosine = models.FloatField()

    objects = SimilarityManager()

    class Meta:
        db_table = u'cg_channel_recommendations'
