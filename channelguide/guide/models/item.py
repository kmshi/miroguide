from datetime import datetime
import os
import urllib2

from django.conf import settings
from sqlalchemy import select

from channelguide import util
from channelguide.db import DBObject, dbutil
from channelguide.guide import feedutil, exceptions
from channelguide.guide.thumbnail import Thumbnailable
import search

class Item(DBObject, Thumbnailable):
    THUMBNAIL_DIR = 'item-thumbnails'
    THUMBNAIL_SIZES = [
            (108, 81),
    ]

    def thumb(self):
        url = self.thumb_url(108, 81)
        return '<img width="108" height="81" src="%s" alt="%s">' % (url, self.name)

    def update_search_data(self):
        if self.search_data is None:
            self.search_data = search.ItemSearchData()
            self.session().save(self.search_data)
        self.search_data.text = ' '.join([self.description, self.url])
        self.search_data.important_text = self.name

    @staticmethod
    def search_for_channel_ids(db_session, terms):
        query = db_session.query(Item)
        where = (search.where_clause(search.ItemSearchData, terms) &
                    query.join_to('search_data'))
        sql_query = select([Item.c.channel_id], where)
        results = db_session.connection(Item.mapper()).execute(sql_query)
        return set([row[0] for row in results])

    def download_thumbnail(self, redownload=False):
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
            self.save_thumbnail(image_data)

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
            updated_parsed = entry['updated_parsed']
            if updated_parsed is None:
                # I think this is a feedparser bug, if you can't parse the
                # updated time, why set the attribute?
                raise KeyError('updated_parsed')
            rv.date = datetime(*updated_parsed[:6])
        except KeyError:
            rv.date = None
        rv.thumbnail_url = feedutil.get_thumbnail_url(entry)
        return rv

    def __str__(self):
        return self.name
