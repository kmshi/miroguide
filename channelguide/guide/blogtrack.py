import feedparser

from models import PCFBlogPost

PCF_BLOG_FEED_URL = 'http://www.getdemocracy.com/news/feed/'

def fetch_new():
    feed = feedparser.parse(PCF_BLOG_FEED_URL)
    posts = []
    for entry in feed.entries:
        post = PCFBlogPost.from_feedparser_entry(entry)
        post.position = len(posts)
        posts.append(post)
    return posts

def update_posts(db_session):
    new_posts = fetch_new()
    old_posts = db_session.query(PCFBlogPost).select()
    for post in old_posts:
        db_session.delete(post)
    for post in new_posts:
        db_session.save(post)
    return new_posts
