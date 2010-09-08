# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

import time

from django.core import cache
from django.db import models

class ChannelSearchDataManager(models.Manager):

    def update(self, channel):
        search_data, created = self.get_or_create(channel=channel)
        search_data.text = self._get_search_data(channel)
        search_data.important_text = channel.name
        search_data.save()
        cache.cache.set('search', time.time())

    @staticmethod
    def _get_search_data(channel):
        simple_attrs = ('description', 'website_url', 'publisher')
        values = [getattr(channel, attr) for attr in simple_attrs]
        values.append(channel.language.name)
        for attr in ('tags', 'categories'):
            for obj in getattr(channel, attr).all():
                values.append(obj.name)
        if channel.url:
            values.append(channel.url)
        return u' '.join(values)

class ChannelSearchData(models.Model):
    channel = models.OneToOneField('channels.Channel', primary_key=True,
                                   related_name='search_data')
    important_text = models.CharField(max_length=255)
    text = models.TextField()

    objects = ChannelSearchDataManager()

    class Meta:
        db_table = 'cg_channel_search_data'

class ItemSearchData(models.Model):
    item = models.OneToOneField('channels.Item', primary_key=True)
    important_text = models.CharField(max_length=255)
    text = models.TextField()

    class Meta:
        db_table = 'cg_item_search_data'


from django.conf import settings
from django.db import connection
from django.db.models import signals

def create_fulltext_indexes(created_models=None, **kwargs):
    """
    Code borrowed from
    http://onebiglibrary.net/story/automatically-create-mysql-fulltext-index-with-django-syncdb
    """
    if ChannelSearchData not in created_models:
        return
    cursor = connection.cursor()
    indexes = [
        ('important_text_index', 'important_text'),
        ('text_index', 'important_text,text')
        ]
    for index, fields in indexes:
        cursor.execute("""
            SELECT * FROM information_schema.statistics
            WHERE table_schema=%s AND table_name='cg_channel_search_data'
            AND index_name=%s
            """, (settings.DATABASE_NAME, index))
        rows = cursor.fetchall()
        if len(rows) == 0:
            print 'Creating fulltext index %s' % index
            cursor.execute("""
                CREATE FULLTEXT INDEX %s
                ON cg_channel_search_data (%s)
                """ % (index, fields))

signals.post_syncdb.connect(create_fulltext_indexes)
