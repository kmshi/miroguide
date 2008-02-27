# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from channelguide.testframework import TestCase
from channelguide.guide import blogtrack

class PCFBlogPostTest(TestCase):

    def test_fetch_new(self):
        """
        blogtrack.fetch_new() should return a list of blog posts.
        """
        posts = blogtrack.fetch_new()
        self.assertNotEquals(len(posts), 0, "didn't download posts")

    def test_update_posts(self):
        """
        blogtrack.update_posts(connection) should delete the old posts
        and replace them.
        """
        fake_post = blogtrack.PCFBlogPost()
        fake_post.title = 'title'
        fake_post.body = 'body'
        fake_post.url = 'url'
        fake_post.position = 0
        fake_post.save(self.connection)
        blogtrack.update_posts(self.connection)
        for post in blogtrack.PCFBlogPost.query().execute(self.connection):
            self.assertNotEquals(post.title, fake_post.title)
            self.assertNotEquals(post.body, fake_post.body)
            self.assertNotEquals(post.url, fake_post.url)
