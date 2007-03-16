from channelguide.db import DBObject
from channelguide.guide import feedutil

class PCFBlogPost(DBObject):
    @staticmethod
    def from_feedparser_entry(entry):
        post = PCFBlogPost()
        post.title = feedutil.to_utf8(entry.title)
        post.body = feedutil.to_utf8(entry.description)
        post.url = entry.link
        return post
