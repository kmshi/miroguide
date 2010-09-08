# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.core.urlresolvers import reverse
from channelguide.channels.models import Channel
from channelguide.labels.models import Tag, Category, Language
from channelguide.testframework import TestCase

class LabelTestBase(TestCase):
    model = None

    def setUp(self):
        TestCase.setUp(self)
        if self.model is not None:
            self.model_name = self.model._meta.object_name.lower()

    def reverse(self, suffix):
        return reverse('%s-%s' % (self.model_name, suffix))

    def test_handles_unicode(self):
        if self.model is None:
            return
        m = self.model.objects.create(name='Hello \u1111')
        self.get_page(self.reverse('index'))
        self.get_page(m.get_absolute_url())

    def test_handles_qmark(self):
        if self.model is None:
            return
        m = self.model.objects.create(name=u'Hello ? World')
        self.get_page(self.reverse('index'))
        self.get_page(m.get_absolute_url())
        self.get_page(m.get_rss_url())

class LabelModerationTestBase(LabelTestBase):

    def setUp(self):
        LabelTestBase.setUp(self)
        self.make_user('joe')
        bobby = self.make_user('bobby')
        bobby.is_superuser = True
        bobby.save()


    def get_labels_from_moderate_page(self):
        response = self.get_page(self.reverse('moderate'))
        return response.context['labels']

    def check_label_names(self, label_list, *names):
        self.assertEquals(len(label_list), len(names))
        for i in range(len(names)):
            self.assertEquals(label_list[i].name, names[i])

    def test_moderate(self):
        if self.model is None:
            return
        self.login('bobby')
        self.assertSameSet(self.get_labels_from_moderate_page(), [])
        self.post_data(self.reverse('add'), {'name': 'russian'})
        self.post_data(self.reverse('add'), {'name': 'english'})
        labels = self.get_labels_from_moderate_page()
        self.assertEquals(len(labels), 2)
        self.check_label_names(labels, 'english', 'russian')
        self.post_data(self.reverse('delete'), {'id': labels[1].id})
        labels = self.get_labels_from_moderate_page()
        self.check_label_names(labels, 'english')
        self.post_data(self.reverse('change'), {'id': labels[0].id,
            'name': 'fooese'})
        labels = self.get_labels_from_moderate_page()
        self.check_label_names(labels, 'fooese')
        self.post_data(self.reverse('change'), {'id': labels[0].id,
                                                         'name': ''})
        labels = self.get_labels_from_moderate_page()
        self.check_label_names(labels, 'fooese')

    def test_moderate_access(self):
        if self.model is None:
            return
        super_mod = self.make_user('wendy', group=['cg_moderator',
                                                   'cg_supermoderator'])
        admin = self.make_user('mork')
        admin.is_superuser = True
        admin.save()
        self.check_page_access(super_mod, self.reverse('moderate'), False)
        self.check_page_access(super_mod, self.reverse('change'), False)
        self.check_page_access(super_mod, self.reverse('add'), False)
        self.check_page_access(super_mod, self.reverse('delete'), False)

        self.check_page_access(admin, self.reverse('moderate'), True)
        self.check_page_access(admin, self.reverse('change'), True)
        self.check_page_access(admin, self.reverse('add'), True)
        self.check_page_access(admin, self.reverse('delete'), True)


class LanguageTestCase(LabelModerationTestBase):
    model = Language

    def setUp(self):
        LabelModerationTestBase.setUp(self)
        self.language.delete()

class CategoryTestCase(LabelModerationTestBase):
    model = Category

class TagTestCase(LabelTestBase):
    model = Tag


class ChannelTagTest(TestCase):
    """Test adding/removing/querying tags from channels."""

    def setUp(self):
        TestCase.setUp(self)
        self.ben = self.make_user('ben')
        self.nick = self.make_user('nick')
        self.channel = self.make_channel(self.ben)

    def check_tags(self, *correct_tags):
        channel = Channel.objects.get(pk=self.channel.id)
        current_tags = [tag.name for tag in channel.tags.distinct()]
        self.assertSameSet(current_tags, correct_tags)

    def test_tags(self):
        self.channel.add_tag(self.ben, 'funny')
        self.check_tags('funny')
        self.channel.add_tag(self.ben, 'cool')
        self.check_tags('funny', 'cool')
        self.channel.add_tags(self.nick, ['sexy', 'cool'])
        self.check_tags('funny', 'cool', 'sexy')
        self.channel.add_tag(self.nick, 'cool')
        self.check_tags('funny', 'cool', 'sexy')

    def test_duplicate_tags(self):
        self.channel.add_tag(self.ben, 'funny')
        self.channel.add_tag(self.nick, 'funny')
        count = Tag.objects.filter(name='funny').count()
        self.assertEquals(count, 1)

    def check_tag_counts(self, name, user_count, channel_count):
        tag = Tag.objects.get(name=name)
        self.assertEquals(tag.tagmap_set.values('user').distinct().count(),
                          user_count)
        self.assertEquals(tag.tagmap_set.values('channel').filter(
                channel__state=Channel.APPROVED).distinct().count(),
                          channel_count)

    def test_info(self):
        # TODO not sure what this is testing
        self.channel.state = Channel.APPROVED
        self.channel.add_tag(self.ben, 'funny')
        self.channel.add_tag(self.nick, 'funny')
        self.channel.save()
        self.check_tag_counts('funny', 2, 1)
        channel2 = self.make_channel(self.nick, state=Channel.APPROVED)
        channel2.add_tags(self.ben, ['tech', 'funny'])
        self.channel.add_tag(self.ben, 'tech')
        self.check_tag_counts('funny', 2, 2)
        self.check_tag_counts('tech', 1, 2)
        non_active = self.make_channel(self.nick)
        non_active.add_tag(self.nick, 'funny')
        non_active.add_tag(self.ben, 'funny')
        self.check_tag_counts('funny', 2, 2)
        self.check_tag_counts('funny', 2, 2)

