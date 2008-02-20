import feedparser

from models import PCFBlogPost

PCF_BLOG_FEED_URL = 'http://getmiro.com/news/feed/'

def fetch_new():
    feed = feedparser.parse(PCF_BLOG_FEED_URL)
    posts = []
    for entry in feed.entries:
        post = PCFBlogPost.from_feedparser_entry(entry)
        post.position = len(posts)
        posts.append(post)
    return posts

def update_posts(connection):
    new_posts = fetch_new()
    old_posts = PCFBlogPost.query().execute(connection)
    for post in old_posts:
        post.delete(connection)
    for post in new_posts:
        post.save(connection)
    connection.commit()
    return new_posts
