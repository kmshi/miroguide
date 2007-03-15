from sqlalchemy import mapper

from channelguide.util import feedutil
import tables

class PCFBlogPost(object):
    @staticmethod
    def from_feedparser_entry(entry):
        post = PCFBlogPost()
        post.title = feedutil.to_utf8(entry.title)
        post.body = feedutil.to_utf8(entry.description)
        post.url = entry.link
        return post

mapper(PCFBlogPost, tables.pcf_blog_post)
