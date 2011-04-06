# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

"""labels.py contains labels that are attached to channels.  This includes
categories which are defined by the moderaters and tags which are
user-created.
"""

from django.db import models
from django.conf import settings
from django.core import cache

from channelguide import util
from django.utils.translation import gettext as _

class Label(models.Model):
    """Label is the base class for both Category and Tag."""

    name = models.CharField(max_length=200)

    class Meta:
        abstract = True
        ordering = ['name']

    def link(self):
        return util.make_link(self.get_url(), self.name)

    def audio_link(self):
        return util.make_link(self.get_audio_url(), self.name)

    def __unicode__(self):
        return self.name

    def __len__(self):
        return len(self.name)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.name)

    def get_absolute_url(self):
        return util.make_absolute_url(self.get_url())


class Category(Label):
    """Categories are created by the admins and assigned to a channel by that
    channel's submitter.
    """

    on_frontpage = models.BooleanField(default=True)

    class Meta(Label.Meta):
        db_table = 'cg_category'

    def get_url(self):
        return util.make_url('genres/%s' % self.name.encode('utf8'),
                             ignore_qmark=True)

    def get_audio_url(self):
        return util.make_url('audio/genres/%s' % self.name.encode('utf8'),
                             ignore_qmark=True)

    def get_rss_url(self):
        return util.make_url('feeds/genres/%s' % self.name.encode('utf8'),
                             ignore_qmark=True)

    def get_list_channels(self, filter_front_page=False,
                          show_state=None, language=None):
        key = 'list-channels:%i:%i:%i:%s:%s' % (
            settings.SITE_ID, self.pk, filter_front_page,
            show_state, language)
        retval = cache.cache.get(key)
        if retval:
            return retval

        def _q(filter_by_rating):
            from channelguide.channels.models import Channel
            query = Channel.objects.approved(archived=0)
            if show_state is not None:
                query = query.filter(state=show_state)
            if language is not None:
                query = query.filter(language=language)
            query = query.filter(categories__in=(self.pk,))
            query = query.order_by('-stats__subscription_count_today')
            if filter_by_rating:
                query = query.filter(rating__average__gt=4)
                query = query.filter(rating__count__gt=4)
                query = query.order_by('-rating__average')
            if filter_front_page:
                query = query.exclude(categories__on_frontpage=False)
            return query

        filter_by_rating = True
        most_popular = _q(filter_by_rating)[:2]
        if len(most_popular) < 2:
            filter_by_rating = False
            most_popular = _q(filter_by_rating)[:2]
        if len(most_popular) > 1:
            first = most_popular[0]
            most_popular = (first, _q(filter_by_rating).exclude(
                    pk=first.pk).order_by('?')[0])
        cache.cache.set(key, most_popular)
        return most_popular


class Tag(Label):
    """Tags are user created labels.  Any string of text can be a tag and any
    user can tag any channel.
    """
    class Meta(Label.Meta):
        db_table = 'cg_tag'

    def get_url(self):
        return util.make_url('tags/%s' % self.name.encode('utf8'),
                             ignore_qmark=True)

    def get_audio_url(self):
        return util.make_url('audio/tags/%s' % self.name.encode('utf8'),
                             ignore_qmark=True)


    def get_rss_url(self):
        return util.make_url('feeds/tags/%s' % self.name.encode('utf8'),
                             ignore_qmark=True)


class TagMap(models.Model):
    channel = models.ForeignKey('channels.Channel')
    tag = models.ForeignKey(Tag)
    user = models.ForeignKey('auth.User')

    class Meta:
        db_table = 'cg_tag_map'
        ordering = []

class Language(Label):
    """Languages are names for the different languages a channel can be in.
    NOTE: we purposely don't associate languages with ISO codes.  ISO codes
    are for written language, which is distinct from spoken language.
    (for example: Mandarin and Cantonese).
    """

    class Meta(Label.Meta):
        db_table = 'cg_channel_language'

    def get_url(self):
        return util.make_url('languages/%s' % self.name,
                             ignore_qmark=True)

    def get_audio_url(self):
        return util.make_url('audio/languages/%s' % self.name.encode('utf8'),
                             ignore_qmark=True)

    def get_rss_url(self):
        return util.make_url('feeds/languages/%s' % self.name,
                             ignore_qmark=True)

    def link(self):
        return util.make_link(self.get_url(), _(self.name))
