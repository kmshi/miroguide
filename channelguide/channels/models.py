
# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from datetime import datetime
import urllib2
from glob import glob
import cgi
import feedparser
import logging
import os
import re
import socket
from xml.sax import saxutils

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

from django.conf import settings
from django.db import models
from django.utils.translation import ngettext
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from channelguide import util
from channelguide.guide import feedutil, exceptions, emailmessages
from channelguide.guide import filetypes

from channelguide.thumbnailable.models import Thumbnailable
from channelguide.moderate.models import ModeratorAction
from channelguide.labels.models import Tag, TagMap


def try_to_download_thumb(url):
    try:
        urlfile = urllib2.urlopen(url)
    except (urllib2.URLError, ValueError, socket.error):
        return None
    return StringIO.StringIO(urlfile.read())

class ChannelManager(models.Manager):

    def approved(self, **kwargs):
        return self.filter(state__in=(Channel.APPROVED, Channel.AUDIO),
                           **kwargs)

    def new(self, **kwargs):
        timestamp = LastApproved.objects.timestamp()
        return self.approved(
            approved_at__lte=timestamp).order_by(
            '-approved_at')


class Channel(Thumbnailable):
    """An RSS feed containing videos for use in Miro."""

    owner = models.ForeignKey('auth.User', related_name='channels')
    name = models.CharField(max_length=255)
    url = models.URLField(max_length=255, null=True, blank=True)
    website_url = models.URLField(max_length=255)
    description = models.TextField()
    hi_def = models.BooleanField()
    language = models.ForeignKey('labels.Language',
                                 db_column='primary_language_id',
                                 related_name='channels')
    publisher = models.CharField(max_length=255)
    state = models.CharField(max_length=1, default='N')
    waiting_for_reply_date = models.DateTimeField(null=True, blank=True)
    modified = models.DateTimeField(auto_now=True)
    creation_time = models.DateTimeField(auto_now_add=True)
    feed_modified = models.DateTimeField(null=True, blank=True)
    feed_etag = models.CharField(max_length=255)
    featured = models.BooleanField(default=False)
    featured_at = models.DateTimeField(null=True, blank=True)
    featured_by = models.ForeignKey('auth.User', related_name='featured_set',
                                    null=True)
    was_featured = models.BooleanField(default=False)
    moderator_shared_at = models.DateTimeField(null=True, blank=True)
    moderator_shared_by = models.ForeignKey(
        'auth.User', null=True,
        related_name='moderator_shared_set')
    approved_at = models.DateTimeField(null=True, blank=True)
    license = models.CharField(max_length=40, default='')
    last_moderated_by = models.ForeignKey('auth.User', null=True,
                                          related_name='last_moderated_set')
    postal_code = models.CharField(max_length=15)
    adult = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)
    geoip = models.CharField(max_length=100, default='')
    categories = models.ManyToManyField('labels.Category',
                                        db_table='cg_category_map',
                                        related_name='channels')
    tags = models.ManyToManyField('labels.Tag', through='labels.TagMap',
                                  related_name='channels')

    objects = ChannelManager()

    class Meta:
        db_table = 'cg_channel'
        permissions = [('add_site', 'Can add a streaming site'),
                       ('change_owner',
                        'Can change the user who owns a channel')]

    NEW = 'N'
    DONT_KNOW = 'D'
    REJECTED = 'R'
    APPROVED = 'A'
    AUDIO = 'U'
    BROKEN = 'B'
    SUSPENDED ='S'

    name_for_state_code = {
        NEW: _('New'),
        APPROVED: _('Approved'),
        DONT_KNOW: _("Don't Know"),
        REJECTED: _("Rejected"),
        SUSPENDED: _("Suspended"),
        AUDIO: _("Audio"),
        BROKEN: _("Broken")
        }

    cc_licence_codes = {
     'Z': 'Not CC Licensed',
     'X': 'Mixed CC Licensing',
     'A': 'Attribution',
     'B': 'Attribution-NoDerivs',
     'C': 'Attribution-NonCommercial-NoDerivs',
     'D': 'Attribution-NonCommercial',
     'E': 'Attribution-NonCommercial-ShareAlike',
     'F': 'Attribution-ShareAlike',
    }

    THUMBNAIL_DIR = 'thumbnails'
    THUMBNAIL_SIZES = [
            (97, 65),
            (165, 110),
            (195, 130),
            (200, 134),
            (245, 164),
    ]

    def __str__(self):
        return "%s (%s)" % (self.name, self.url)

    def __repr__(self):
        return "Channel(%r, %r)" % (self.name, self.url)

    def get_state_name(self):
        return self.name_for_state_code.get(self.state, _("Unknown"))
    state_name = property(get_state_name)

    def get_url(self):
        if self.url:
            if self.state == Channel.AUDIO:
                head = 'audio'
            else:
                head = 'feeds'
        else:
            head = 'sites'
        return util.make_url('%s/%i' % (head, self.id))

    def get_absolute_url(self):
        return util.make_absolute_url(self.get_url())

    def get_edit_url(self):
        return self.get_url() + '/edit'

    def subscription_link(self):
        cg_link = self.get_subscribe_hit_url()
        subscribe_link = self.get_subscription_url()
        return util.make_link_attributes(subscribe_link,
                onclick="return handleSubscriptionLink('%s', '%s');" %
                (cg_link, subscribe_link))

    def get_subscribe_hit_url(self):
        return self.get_absolute_url() + '/subscribe-hit'

    def get_user_add_url(self):
        return self.get_absolute_url() + '/add'

    def get_subscription_url(self):
        if self.url:
            if self.state == Channel.AUDIO:
                section = 'audio'
            else:
                section = 'video'
            return util.get_subscription_url(
                self.url,
                trackback=self.get_subscribe_hit_url(),
                section=section)
        else:
            return util.get_subscription_url(
                self.website_url,
                type='site',
                trackback=self.get_subscribe_hit_url())

    def get_flag_url(self):
        return self.get_absolute_url() + '/flag'

    def is_approved(self):
        return self.state in (self.APPROVED, self.AUDIO)

    def add_tag(self, user, tag_name):
        """Add a tag to this channel."""
        tag, created = Tag.objects.get_or_create(name=tag_name)
        TagMap.objects.get_or_create(channel=self,
                                     user=user,
                                     tag=tag)

    def delete_tag(self, user, tag_name):
        try:
            tag = Tag.objects.get(name=tag_name)
        except Tag.DoesNotExit:
            return
        try:
            tag_map = TagMap.objects.get(channel=self.id,
                                         user=user,
                                         tag=tag)
        except TagMap.DoesNotExist:
            return
        else:
            tag_map.delete()

    def add_tags(self, user, tags):
        """Tag this channel with a list of tags."""
        for tag in tags:
            self.add_tag(user, tag)

    def get_tags_for_user(self, user):
        return [map.tag for map in
                TagMap.objects.filter(user=user, channel=self)]

    def get_tags_for_owner(self):
        return self.get_tags_for_user(self.owner)

    def get_subscription_str(self):
        return ngettext('%(count)d subscriber',
                '%(count)d subscribers', self.subscriptions.count) % {
                'count': self.subscriptions.count
        }

    def get_episodes_str(self):
        count = self.item_info.count
        return ngettext('%(count)d episode', '%(count)d episodes', count) % {
                'count': count
        }

    def update_thumbnails(self, overwrite=False, sizes=None):
        """Recreate the thumbnails using the original data."""

        if self.thumbnail_extension is None:
            pattern = self.thumb_path('original')
            pattern = pattern.replace("missing.png", "%d.*" % self.id)
            matches = glob(pattern)
            if matches:
                self.thumbnail_extension = util.get_image_extension(
                    file(matches[0]))
                self.save()

        Thumbnailable.refresh_thumbnails(self, overwrite, sizes)
        for item in self.items.order_by('-id'):
            try:
                item.refresh_thumbnails(overwrite, sizes)
            except: pass

    def download_item_thumbnails(self, redownload=False):
        """Download item thumbnails."""

        for item in self.items.all():
            # try:
                item.download_thumbnail(redownload)
            # except:
            #     pass

    def get_missing_image_url(self, width, height):
        return ''

    def can_edit(self, user):
        return user.id == self.owner_id or \
            user.has_perm('channels.change_channel')

    def download_feed(self):
        if self.feed_modified:
            modified = self.feed_modified.timetuple()
        else:
            modified = None
        parsed = feedparser.parse(self.url, modified=modified,
                etag=self.feed_etag)
        if hasattr(parsed, 'status') and parsed.status == 304:
            return None
        if hasattr(parsed, 'modified'):
            new_modified = feedutil.struct_time_to_datetime(parsed.modified)
            if (self.feed_modified is not None and
                    new_modified <= self.feed_modified):
                return None
            self.feed_modified = new_modified
        if hasattr(parsed, 'etag'):
            self.feed_etag = parsed.etag
        return parsed

    def update_items(self, feedparser_input=None):
        if self.url is None:
            return # sites don't have items
        try:
            if feedparser_input is None:
                parsed = self.download_feed()
                if parsed is None:
                    if self.items or self.state != Channel.SUSPENDED:
                        self._check_archived()
                    return
            else:
                parsed = feedparser.parse(feedparser_input)
        except:
            logging.exception("ERROR parsing %s" % self.url)
        else:
            if parsed.bozo and isinstance(parsed.bozo_exception,
                                          urllib2.URLError):
                # don't do anything for URLErrors
                # XXX maybe try again?
                return
            items = []
            for entry in parsed.entries:
                try:
                    items.append(Item.from_feedparser_entry(entry))
                except exceptions.EntryMissingDataError:
                    pass
                except exceptions.FeedparserEntryError, e:
                    logging.warn("Error converting feedparser entry: %s (%s)"
                            % (e, self))
            self._replace_items(items)
        if self.items.count():
            self._check_archived()
        else:
            miroguide = User.objects.get(username='miroguide')
            if self.state == Channel.SUSPENDED:
                latest_moderator_action = self.moderator_actions.order_by(
                    '-id')[0]
                if (datetime.now() -
                    latest_moderator_action.timestamp).days > 90:
                    self.change_state(miroguide, Channel.REJECTED)
                    return
            self.archived = True
            self.change_state(miroguide, Channel.SUSPENDED)

    def _check_archived(self):
        latest = None
        if self.state == Channel.SUSPENDED:
            # we can unsuspend, since we've got items
            if self.moderator_actions.count() == 1: # was a NEW feed
                self.state = Channel.NEW
                self.last_moderated_by_id = None
            else:
                for last_action in self.moderator_actions.all():
                    if last_action.action != Channel.SUSPENDED:
                        break
                    else:
                        last_action.delete()
                if last_action.action != Channel.SUSPENDED:
                    self.state = last_action.action
                    self.last_moderated_by_id = last_action.user_id
                    if self.state == Channel.APPROVED:
                        self.approved_at = last_action.timestamp
                else:
                    self.state = Channel.NEW
                    self.last_moderated_by_id = None
            self.save()
        items = [item for item in self.items.all() if item.date is not None]
        if not items:
            return
        items.sort(key=lambda x: x.date)
        latest = items[-1].date
        if (datetime.now() - latest).days > 90:
            self.archived = True
        else:
            self.archived = False
        self.save()

    def _replace_items(self, new_items):
        """Replace the items currently in the channel with a new list of
        items."""

        to_delete = set(self.items.all())
        to_add = set(new_items)

        items_by_url = {}
        items_by_guid = {}
        for i in self.items.all():
            if i.url is not None:
                items_by_url[i.url] = i
            if i.get_guid() is not None:
                items_by_guid[i.get_guid()] = i
        for i in new_items:
            if i.get_guid() in items_by_guid:
                to_delete.discard(items_by_guid[i.get_guid()])
                to_add.discard(i)
                items_by_guid[i.get_guid()].update_from_item(i)
            elif i.url in items_by_url:
                to_delete.discard(items_by_url[i.url])
                to_add.discard(i)
                items_by_url[i.url].update_from_item(i)
        for i in to_delete:
            i.delete()
        for i in new_items:
            if i in to_add:
                self.items.add(i)

    def _thumb_html(self, width, height):
        thumb_url = self.thumb_url(width, height)
        return util.mark_safe(
            '<img class="hasCorners" src="%s" alt="%s">' %
            (thumb_url, cgi.escape(self.name)))

    def fake_feature_thumb(self):
        thumb_url = self.thumb_url(252, 169)
        return 'src: "%s" alt:"%s"' % (thumb_url, cgi.escape(self.name))

    def name_as_link(self):
        return util.make_link(self.get_absolute_url(), self.name)

    def website_link(self):
        url_label = self.website_url
        url_label = util.chop_prefix(url_label, 'http://')
        url_label = util.chop_prefix(url_label, 'https://')
        url_label = util.chop_prefix(url_label, 'www.')
        return util.make_link(self.website_url, url_label)

    def change_state(self, user, newstate):
        if self.state == newstate and self.last_moderated_by == user:
            self.save()
            return
        self.state = newstate
        if self.is_approved():
            self.approved_at = datetime.now()
            if self.owner.email:
                emailmessages.ApprovalEmail(self, self.owner).send_email()
            else:
                logging.warn('not sending approval message for channel %d '
                        '(%s) because the owner email is not set', self.id,
                        self.name)
            self.update_items()
        else:
            self.approved_at = None
        self.last_moderated_by = user
        self.save()
        ModeratorAction(user=user, channel=self, action=newstate).save()

    def change_featured(self, user):
        if user is not None:
            self.featured = True
            self.featured_at = datetime.now()
            self.featured_by_id = user.id
        else:
            self.featured = False
            self.featured_at = None
            self.featured_by_id = None
        self.save()

    def toggle_moderator_share(self, user):
        if self.moderator_shared_at is None:
            self.moderator_shared_at = datetime.now()
            self.moderator_shared_by = user
        else:
            self.moderator_shared_at = None
            self.moderator_shared_by = None
        self.save()

    def can_appear_on_frontpage(self):
        return not bool(self.categories.filter(on_frontpage=False).count())

class AddedChannel(models.Model): # TODO move
    channel = models.ForeignKey(Channel, db_index=True,
                                related_name='added_channels')
    user = models.ForeignKey(User, db_index=True,
                             related_name='added_channels')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cg_channel_added'
        unique_together = [('channel', 'user')]

class Item(Thumbnailable):
    channel = models.ForeignKey(Channel, related_name='items')
    url = models.URLField(max_length=255)
    name = models.CharField(max_length=255)
    description = models.TextField()
    mime_type = models.CharField(max_length=50)
    thumbnail_url = models.CharField(max_length=255, blank=True, null=True)
    size = models.IntegerField()
    guid = models.CharField(max_length=255)
    date = models.DateTimeField()

    class Meta:
        db_table = 'cg_channel_item'
        ordering = ['-date', '-id']

    THUMBNAIL_DIR = 'item-thumbnails'
    THUMBNAIL_SIZES = [
            (97, 65),
            (200, 134),
    ]

    def get_url(self):
        return '/items/%i' % self.id

    def get_absolute_url(self):
        return util.make_absolute_url(self.get_url())

    def get_guid(self):
        try:
            return self.guid
        except AttributeError:
            return None

    def get_missing_image_url(self, width, height):
        return self.channel.thumb_url(width, height)

    def thumb(self):
        url = self.thumb_url(97, 65)
        return util.mark_safe(
            '<img width="97" height="68" src="%s" alt="%s">' % (
                url, self.name.replace('"', "'")))

    def download_url(self):
        data = {
            'title1': self.name,
            'description1': self.description,
            'length1': str(self.size),
            'type1': self.mime_type,
            'thumbnail1': self.thumb_url(200, 133),
            'url1': self.url
            }
        return settings.DOWNLOAD_URL + util.format_get_data(data)

    def linked_name(self):
        return '<a href="%s">%s</a>' % (self.download_url(), self.name)

    def update_search_data(self):
        raise NotImplementedError # not doing this right now
        if self.search_data is None:
            #self.search_data = search.ItemSearchData()
            self.search_data.item_id = self.id
        self.search_data.text = ' '.join([self.description, self.url])
        self.search_data.important_text = self.name
        self.search_data.save()

    def download_thumbnail(self, redownload=False):
        if self.thumbnail_url is None:
            return
        if (not self.thumbnail_exists()) or redownload:
            util.ensure_dir_exists(settings.IMAGE_DOWNLOAD_CACHE_DIR)
            cache_path = os.path.join(settings.IMAGE_DOWNLOAD_CACHE_DIR,
                    util.hash_string(self.thumbnail_url))
            if os.path.exists(cache_path) and not redownload:
                image_file = file(cache_path, 'rb')
            else:
                url = self.thumbnail_url[:8] + self.thumbnail_url[8:].replace(
                    '//', '/')
                image_file = try_to_download_thumb(url)
                if image_file is None:
                    return
                util.copy_obj(cache_path, image_file)
            self.save_thumbnail(image_file)

    @staticmethod
    def from_feedparser_entry(entry):
        # XXX Added some hacks to get a decent item out of YouTube after they
        # stopped having enclosures (2008-1-21).
        enclosure = feedutil.get_first_video_enclosure(entry)
        if enclosure is None:
            if 'link' not in entry:
                raise exceptions.FeedparserEntryError(
                    "No video enclosure and ngo link")
            if entry['link'].find('youtube.com') == -1:
                if not filetypes.isAllowedFilename(entry['link']):
                    raise exceptions.EntryMissingDataError('Link is invalid')
        rv = Item()
        try:
            rv.name = feedutil.to_utf8(entry['title'])
            if enclosure is not None:
                rv.url = feedutil.to_utf8(enclosure['href'])
                # split off the front if there's additional data in the
                # MIME type
                if 'type' in enclosure:
                    rv.mime_type = feedutil.to_utf8(enclosure['type']
                                                    ).split(';', 1)[0]
                else:
                    rv.mime_type = 'video/unknown'
            elif entry['link'].find('youtube.com') != -1:
                rv.url = entry['link']
                rv.mime_type = 'video/x-flv'
            else:
                rv.url = entry['link']
                rv.mime_type = filetypes.guessMimeType(rv.url)
            if enclosure is not None and 'text' in enclosure:
                rv.description = feedutil.to_utf8(enclosure['text'])
            elif 'description' in entry:
                rv.description = feedutil.to_utf8(entry['description'])
            elif 'media_description' in entry:
                rv.description = feedutil.to_utf8(entry['media_description'])
            elif entry.get('link', '').find('youtube.com') != -1:
                match = re.search(r'<div><span>(.*?)</span></div>',
                                  rv.description, re.S)
                if match:
                    rv.description = feedutil.to_utf8(
                        saxutils.unescape(match.group(1)))
            rv.description # this will raise an AttributeError if it wasn't set
        except (AttributeError, KeyError), e:
            raise exceptions.EntryMissingDataError(e.args[0])
        if enclosure is not None:
            try:
                rv.size = int(feedutil.to_utf8(enclosure['length']))
            except (KeyError, ValueError):
                rv.size = 0
        try:
            rv.guid = feedutil.to_utf8(entry['id'])
        except KeyError:
            rv.guid = None
        try:
            updated_parsed = entry['updated_parsed']
            if updated_parsed is None:
                # I think this is a feedparser bug, if you can't parse the
                # updated time, why set the attribute?
                raise KeyError('updated_parsed')
            rv.date = feedutil.struct_time_to_datetime(updated_parsed)
        except KeyError:
            rv.date = None
        rv.thumbnail_url = feedutil.get_thumbnail_url(entry)
        return rv

    def update_from_item(self, other):
        """
        Update our information from another item, presumed to be the same as
        this one.
        """
        for field, value in other.__dict__.items():
            if not field.endswith('id'):
                setattr(self, field, value)
        self.save()

    def __str__(self):
        return self.name

    def __hash__(self):
        # make sure that unsaved objects are still unique
        if self.pk:
            return self.pk
        else:
            return id(self)

class LastApprovedManager(models.Manager):

    def timestamp(self):
        try:
            last_approved = self.get()
        except self.model.DoesNotExist:
            last_approved = self.model(
                timestamp=datetime.now())
            last_approved.save()
        return last_approved.timestamp

class LastApproved(models.Model):
    timestamp = models.DateTimeField(primary_key=True)

    objects = LastApprovedManager()

    class Meta:
        db_table = 'cg_channel_last_approved'


for width, height in Channel.THUMBNAIL_SIZES:
    def channel_thumb(self, width=width, height=height):
        return self._thumb_html(width, height)
    def channel_thumb_url(self, width=width, height=height):
        return self.thumb_url(width, height)
    setattr(Channel, 'thumb_%i_%i' % (width, height), channel_thumb)
    setattr(Channel, 'thumb_url_%i_%i' % (width, height), channel_thumb_url)
    del channel_thumb, channel_thumb_url


for width, height in Item.THUMBNAIL_SIZES:
    def item_thumb_url(self, width=width, height=height):
        return self.thumb_url(width, height)
    setattr(Item, 'thumb_url_%i_%i' % (width, height), item_thumb_url)
    del item_thumb_url
