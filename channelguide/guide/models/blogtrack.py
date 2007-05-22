from sqlhelper.orm import Record
from channelguide.guide import feedutil, tables

class PCFBlogPost(Record):
    table = tables.pcf_blog_post

    @staticmethod
    def from_feedparser_entry(entry):
        post = PCFBlogPost()
        post.title = feedutil.to_utf8(entry.title)
        post.body = feedutil.to_utf8(entry.description)
        post.url = entry.link
        return post
