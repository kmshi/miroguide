from datetime import datetime
import urllib2

from channelguide.db import DBObject
from channelguide.guide import feedutil
from channelguide.guide.thumbnail import Thumbnailable
from channelguide.guide.exceptions import FeedparserEntryError
from search import FullTextSearchable, ItemSearchData

class Item(DBObject, Thumbnailable, FullTextSearchable):
    THUMBNAIL_DIR = 'item-thumbnails'
    THUMBNAIL_SIZES = [
            (108, 81),
    ]

    search_data_class = ItemSearchData
    search_attributes = ('description', 'url')
    search_attributes_important = ('name', )

    def thumb(self):
        url = self.thumb_url(108, 81)
        return '<img width="108" height="81" src="%s" alt="%s">' % (url, self.name)

    def download_thumbnail(self):
        if self.thumbnail_url is not None:
            try:
                image_data = urllib2.urlopen(self.thumbnail_url).read()
            except urllib2.URLError, ValueError:
                pass
            else:
                self.save_thumbnail(image_data)

    @staticmethod
    def from_feedparser_entry(entry):
        enclosure = feedutil.get_first_video_enclosure(entry)
        if enclosure is None:
            raise FeedparserEntryError("No video enclosure")
        rv = Item()
        try:
            rv.name = feedutil.to_utf8(entry['title'])
            rv.url = feedutil.to_utf8(enclosure['url'])
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
            rv.mime_type = feedutil.to_utf8(enclosure['type'])
        except KeyError, e:
            raise FeedparserEntryError("Missing required data: %s" %
                    e.args[0])
        try:
            rv.size = feedutil.to_utf8(enclosure['length'])
        except KeyError:
            rv.size = None
        try:
            rv.date = datetime(*entry['updated_parsed'][:6])
        except KeyError:
            rv.date = None
        rv.thumbnail_url = feedutil.get_thumbnail_url(entry)
        return rv

    def __str__(self):
        return self.name

