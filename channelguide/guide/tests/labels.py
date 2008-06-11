# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from channelguide.guide.models import User, Category, Language, Tag
from channelguide.testframework import TestCase

class LabelModerationTestBase(TestCase):

    label_url = None
    def setUp(self):
        TestCase.setUp(self)
        self.make_user('joe')
        self.make_user('bobby', role=User.ADMIN)

    def get_labels_from_moderate_page(self):
        response = self.get_page(self.label_url + "/moderate")
        return response.context[0]['categories']

    def check_label_names(self, label_list, *names):
        self.assertEquals(len(label_list), len(names))
        for i in range(len(names)):
            self.assertEquals(label_list[i].name, names[i])

    def test_moderate(self):
        self.login('bobby')
        self.assertSameSet(self.get_labels_from_moderate_page(), [])
        self.post_data(self.label_url + "/add", {'name': 'russian'})
        self.post_data(self.label_url + "/add", {'name': 'english'})
        labels = self.get_labels_from_moderate_page()
        self.assertEquals(len(labels), 2)
        self.check_label_names(labels, 'english', 'russian')
        self.post_data(self.label_url + "/delete", {'id': labels[1].id})
        labels = self.get_labels_from_moderate_page()
        self.check_label_names(labels, 'english')
        self.post_data(self.label_url + "/change_name", {'id': labels[0].id,
            'name': 'fooese'})
        labels = self.get_labels_from_moderate_page()
        self.check_label_names(labels, 'fooese')
        self.post_data(self.label_url + '/change_name', {'id': labels[0].id,
                                                         'name': ''})
        labels = self.get_labels_from_moderate_page()
        self.check_label_names(labels, 'fooese')

    def test_moderate_access(self):
        super_mod = self.make_user('wendy', role=User.SUPERMODERATOR)
        admin = self.make_user('mork', role=User.ADMIN)
        self.check_page_access(super_mod, self.label_url + "/moderate", False)
        self.check_page_access(super_mod, self.label_url + "/change_name", False)
        self.check_page_access(super_mod, self.label_url + "/add", False)
        self.check_page_access(super_mod, self.label_url + "/delete", False)

        self.check_page_access(admin, self.label_url + "/moderate", True)
        self.check_page_access(admin, self.label_url + "/change_name", True)
        self.check_page_access(admin, self.label_url + "/add", True)
        self.check_page_access(admin, self.label_url + "/delete", True)

class LabelTestBase(TestCase):
    model = None
    label_url = None

    def test_handles_unicode(self):
        m = self.model(u'Hello \u1111')
        self.save_to_db(m)
        self.get_page(self.label_url + '/')
        self.get_page(m.get_url())

class LanguageTestCase(LabelModerationTestBase, LabelTestBase):
    label_url = '/languages'
    model = Language

    def setUp(self):
        LabelModerationTestBase.setUp(self)
        self.language.delete(self.connection)
        self.refresh_connection()

class CategoryTestCase(LabelModerationTestBase, LabelTestBase):
    label_url = '/categories'
    model = Category

class TagTestCase(LabelTestBase):
    label_url = '/tags'
    model = Tag

__all__ = ['LanguageTestCase', 'CategoryTestCase', 'TagTestCase']
