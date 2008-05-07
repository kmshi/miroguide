# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from datetime import datetime
import os
import urllib2

from django.conf import settings

from channelguide import util
from channelguide.guide import feedutil, filetypes, exceptions, tables
from channelguide.guide.thumbnail import Thumbnailable
from sqlhelper.orm import Record
import search

class Item(Record, Thumbnailable):
    table = tables.item

    THUMBNAIL_DIR = 'item-thumbnails'
    THUMBNAIL_SIZES = [
            (200, 133),
    ]

    def get_guid(self):
        try:
            return self.guid
        except AttributeError:
            return None

    def get_missing_image_url(self, width, height):
        return self.channel.thumb_url(200, 133)

    def thumb(self):
        url = self.thumb_url(200, 133)
        return util.mark_safe('<img width="200" height="133" src="%s" alt="%s">' % (url, self.name.replace('"', "'")))

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

    def update_search_data(self, connection):
        self.join('search_data').execute(connection)
        if self.search_data is None:
            self.search_data = search.ItemSearchData()
            self.search_data.item_id = self.id
        self.search_data.text = ' '.join([self.description, self.url])
        self.search_data.important_text = self.name
        self.search_data.save(connection)

    def download_thumbnail(self, connection, redownload=False):
        if self.thumbnail_url is None:
            return
        if (not self.thumbnail_exists()) or redownload:
            util.ensure_dir_exists(settings.IMAGE_DOWNLOAD_CACHE_DIR)
            cache_path = os.path.join(settings.IMAGE_DOWNLOAD_CACHE_DIR,
                    util.hash_string(self.thumbnail_url))
            if os.path.exists(cache_path) and not redownload:
                image_data = util.read_file(cache_path)
            else:
                try:
                    url = self.thumbnail_url[:8] + self.thumbnail_url[8:].replace('//', '/')
                    image_data = urllib2.urlopen(url).read()
                except urllib2.URLError, ValueError:
                    return
                else:
                    util.write_file(cache_path, image_data)
            self.save_thumbnail(connection, image_data)

    @staticmethod
    def from_feedparser_entry(entry):
        enclosure = feedutil.get_first_video_enclosure(entry)
        if enclosure is None:
            if 'link' not in entry:
                raise exceptions.FeedparserEntryError("No video enclosure and no link")
            if not filetypes.isAllowedFilename(entry['link']):
                raise exceptions.EntryMissingDataError('Link is invalid')
        rv = Item()
        try:
            rv.name = feedutil.to_utf8(entry['title'])
            if enclosure is not None:
                rv.url = feedutil.to_utf8(enclosure['url'])
                rv.mime_type = feedutil.to_utf8(enclosure['type'])
            else:
                rv.url = entry['link']
                rv.mime_type = filetypes.guessMimeType(rv.url)
            try:
                if enclosure is None:
                    raise KeyError
                rv.desciption = feedutil.to_utf8(enclosure['text'])
            except KeyError:
                try:
                    rv.description = feedutil.to_utf8(entry.description)
                except AttributeError:
                    # this is a weird hack, for some reason if we use
                    # entry['description'] and it isn't present a feedparser
                    # raises a TypeError instead of a KeyError
                    raise KeyError('description')
        except KeyError, e:
            raise exceptions.EntryMissingDataError(e.args[0])
        if enclosure is not None:
            try:
                rv.size = feedutil.to_utf8(enclosure['length'])
            except KeyError:
                rv.size = None
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

    def __str__(self):
        return self.name
