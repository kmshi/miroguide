from datetime import datetime
import os
import urllib2

from django.conf import settings

from channelguide import util
from channelguide.guide import feedutil, exceptions, tables
from channelguide.guide.thumbnail import Thumbnailable
from sqlhelper.orm import Record
import search

class Item(Record, Thumbnailable):
    table = tables.item

    THUMBNAIL_DIR = 'item-thumbnails'
    THUMBNAIL_SIZES = [
            (108, 81),
    ]

    def get_guid(self):
        try:
            return self.guid
        except AttributeError:
            return None

    def thumb(self):
        url = self.thumb_url(108, 81)
        return '<img width="108" height="81" src="%s" alt="%s">' % (url, self.name)

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
        if not self.thumbnail_exists() or redownload:
            util.ensure_dir_exists(settings.IMAGE_DOWNLOAD_CACHE_DIR)
            cache_path = os.path.join(settings.IMAGE_DOWNLOAD_CACHE_DIR,
                    util.hash_string(self.thumbnail_url))
            if os.path.exists(cache_path):
                image_data = util.read_file(cache_path)
            else:
                try:
                    image_data = urllib2.urlopen(self.thumbnail_url).read()
                except urllib2.URLError, ValueError:
                    return
                else:
                    util.write_file(cache_path, image_data)
            self.save_thumbnail(connection, image_data)

    @staticmethod
    def from_feedparser_entry(entry):
        enclosure = feedutil.get_first_video_enclosure(entry)
        if enclosure is None:
            raise exceptions.FeedparserEntryError("No video enclosure")
        rv = Item()
        try:
            rv.name = feedutil.to_utf8(entry['title'])
            rv.url = feedutil.to_utf8(enclosure['url'])
            rv.mime_type = feedutil.to_utf8(enclosure['type'])
            try:
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
