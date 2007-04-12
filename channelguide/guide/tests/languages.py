from channelguide.guide.models import User
from channelguide.testframework import TestCase

class LanguageTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.db_session.delete(self.language)
        self.db_session.flush()
        self.make_user('joe')
        self.make_user('bobby', role=User.MODERATOR)

    def get_languages_from_moderate_page(self):
        response = self.get_page("/languages/moderate")
        return response.context[0]['languages']

    def check_language_names(self, language_list, *names):
        self.assertEquals(len(language_list), len(names))
        for i in range(len(names)):
            self.assertEquals(language_list[i].name, names[i])

    def test_moderate(self):
        self.login('bobby')
        self.assertEquals(self.get_languages_from_moderate_page(), [])
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
        super_mod = self.make_user('wendy', role=User.SUPER_MODERATOR)
        admin = self.make_user('mork', role=User.ADMIN)
        self.check_page_access(super_mod, "/language_list/change_name", False)
        self.check_page_access(super_mod, "/language_list/add", False)
        self.check_page_access(super_mod, "/language_list/delete", False)

        self.check_page_access(admin, "/language_list/change_name", True)
        self.check_page_access(admin, "/language_list/add", True)
        self.check_page_access(admin, "/language_list/delete", True)
