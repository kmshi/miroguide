from channelguide.guide.models import User
from channelguide.testframework import TestCase

class LanguageTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.language.delete(self.connection)
        self.make_user('joe')
        self.make_user('bobby', role=User.ADMIN)

    def get_languages_from_moderate_page(self):
        response = self.get_page("/languages/moderate")
        return response.context[0]['categories']

    def check_language_names(self, language_list, *names):
        self.assertEquals(len(language_list), len(names))
        for i in range(len(names)):
            self.assertEquals(language_list[i].name, names[i])

    def test_moderate(self):
        self.login('bobby')
        self.assertSameSet(self.get_languages_from_moderate_page(), [])
        self.post_data("/languages/add", {'name': 'russian'})
        self.post_data("/languages/add", {'name': 'english'})
        languages = self.get_languages_from_moderate_page()
        self.assertEquals(len(languages), 2)
        self.check_language_names(languages, 'english', 'russian')
        self.post_data("/languages/delete", {'id': languages[1].id})
        languages = self.get_languages_from_moderate_page()
        self.check_language_names(languages, 'english')
        self.post_data("/languages/change_name", {'id': languages[0].id,
            'name': 'fooese'})
        languages = self.get_languages_from_moderate_page()
        self.check_language_names(languages, 'fooese')

    def test_moderate_access(self):
        super_mod = self.make_user('wendy', role=User.SUPERMODERATOR)
        admin = self.make_user('mork', role=User.ADMIN)
        self.check_page_access(super_mod, "/languages/moderate", False)
        self.check_page_access(super_mod, "/languages/change_name", False)
        self.check_page_access(super_mod, "/languages/add", False)
        self.check_page_access(super_mod, "/languages/delete", False)

        self.check_page_access(admin, "/languages/moderate", True)
        self.check_page_access(admin, "/languages/change_name", True)
        self.check_page_access(admin, "/languages/add", True)
        self.check_page_access(admin, "/languages/delete", True)
