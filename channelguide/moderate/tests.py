# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.core import mail
from django.core.urlresolvers import reverse

from channelguide.channels.models import Channel
from channelguide.flags.models import Flag
from channelguide.testframework import TestCase

class ModerateTestCase(TestCase):
    """Test the moderate channel web page."""

    def setUp(self):
        TestCase.setUp(self)
        self.ralph = self.make_user('ralph')
        self.channel = self.make_channel(self.ralph)
        self.supermod = self.make_user('supermod',
                                       group=['cg_supermoderator',
                                              'cg_moderator'])
        self.joe = self.make_user('joe', group='cg_moderator')
        self.schmoe = self.make_user('schmoe')

    def login(self, username):
        TestCase.login(self, username)
        return self.get_page('/moderate')

    def test_moderator_required(self):
        response = self.get_page('/moderate')
        self.assertEquals(response.status_code, 302)
        response = self.login('schmoe')
        self.assertEquals(response.status_code, 302)
        response = self.login('joe')
        self.assertEquals(response.status_code, 200)

    def test_moderate_action(self):
        self.login('joe')
        def check_state(action, state):
            self.channel.state = Channel.NEW
            self.channel.url = None
            self.channel.save()
            url = self.channel.get_url()
            self.post_data(url, {'action': 'change-state', 'submit': action})
            self.assertEquals(Channel.objects.get(pk=self.channel.pk).state,
                              state)
        check_state('Approve', Channel.APPROVED)
        check_state("Don't Know", Channel.DONT_KNOW)

    def test_approve_without_owner_email(self):
        self.channel.owner.email = ''
        self.channel.owner.save()
        self.channel.url = None
        self.channel.save()
        self.login('joe')
        url = self.channel.get_url()
        self.pause_logging()
        self.post_data(url, {'action': 'change-state', 'submit':
            'Approve'})
        self.check_logging(warnings=1)
        self.resume_logging()
        self.assertEquals(len(mail.outbox), 0)

    def _add_flags(self):
        Flag.objects.get_or_create(channel=self.channel, user=self.joe,
                            flag=Flag.NOT_HD)
        Flag.objects.get_or_create(channel=self.channel, user=self.joe,
                            flag=999)

    def test_toggle_hd(self):
        """
        The 'toggle-hd' action should flip the hi_def bit on the channel.
        Additionally, when toggling HD on the HD flags should be cleared.
        """
        self._add_flags()
        self.assertEquals(self.channel.hi_def, False)
        url = self.channel.get_url()
        self.post_data(url, {'action': 'toggle-hd'}, self.joe)
        new_channel = Channel.objects.get(pk=self.channel.pk)
        self.assertEquals(new_channel.hi_def, True)
        self.assertEquals(new_channel.flags.count(), 1)

        self._add_flags()
        self.post_data(url, {'action': 'toggle-hd'}, self.joe)
        new_channel = Channel.objects.get(pk=self.channel.pk)
        self.assertEquals(new_channel.hi_def, False)
        self.assertEquals(new_channel.flags.count(), 2)

    def test_toggle_hd_requires_moderator(self):
        """
        Toggling the HD flag should require a moderator.
        """
        self.assertEquals(self.channel.hi_def, False)
        url = self.channel.get_url()
        self.post_data(url, {'action': 'toggle-hd'})
        self.assertEquals(Channel.objects.get(pk=self.channel.pk).hi_def,
                          False)


    def test_set_hd(self):
        """
        The 'set-id' action should turn HD on if 'value' is 'on', and off
        otherwise.  It should also clear the flags.
        """
        self._add_flags()
        self.assertEquals(self.channel.hi_def, False)
        url = self.channel.get_url()
        self.post_data(url, {'action': 'set-hd', 'value': 'On'}, self.joe)
        new_channel = Channel.objects.get(pk=self.channel.pk)
        self.assertEquals(new_channel.hi_def, True)
        self.assertEquals(new_channel.flags.count(), 1)

        self._add_flags()
        self.post_data(url, {'action': 'set-hd', 'value': 'off'}, self.joe)
        new_channel = Channel.objects.get(pk=self.channel.pk)
        self.assertEquals(new_channel.hi_def, False)
        self.assertEquals(new_channel.flags.count(), 1)

    def test_reject(self):
        self.login('joe')
        def check_rejection_button(action):
            self.channel.state = Channel.NEW
            self.channel.save()
            starting_email_count = len(mail.outbox)
            before_count = Channel.objects.get(
                pk=self.channel.pk).notes.count()
            url = self.channel.get_url()
            self.post_data(url, {'action': 'standard-reject',
                                 'submit': action})
            after = Channel.objects.get(pk=self.channel.pk)
            self.assertEquals(after.state, Channel.REJECTED)
            self.assertEquals(after.notes.count(), before_count + 1)
            self.assertEquals(len(mail.outbox), starting_email_count + 1)
        check_rejection_button('Broken')
        check_rejection_button('Copyrighted')
        check_rejection_button('Explicit')
        check_rejection_button('No Media')

    def test_custom_reject(self):
        self.login('joe')
        body = 'CUSTOM BODY'
        url = self.channel.get_url()
        self.post_data(url, {'action': 'reject', 'body':
            body})
        updated = Channel.objects.get(pk=self.channel.pk)
        self.assertEquals(updated.state, Channel.REJECTED)
        self.assertEquals(updated.notes.count(), 1)
        self.assertEquals(updated.notes.all()[0].body, body)
        self.assertEquals(len(mail.outbox), 1)

    def test_custom_reject_needs_body(self):
        self.login('joe')
        url = self.channel.get_url()
        self.post_data(url, {'action': 'reject', 'body':
            ''})
        updated = Channel.objects.get(pk=self.channel.pk)
        self.assertEquals(updated.state, Channel.NEW)

    def test_approve_and_feature_email(self):
        self.channel.url = None
        self.channel.save()
        self.login('supermod')
        url = self.channel.get_url()
        self.post_data(url, {'action': 'email', 'type':'Approve & Feature',
            'body': 'body', 'email':'email@address.com'})
        updated = Channel.objects.get(pk=self.channel.pk)
        self.assertEquals(updated.state, Channel.APPROVED)
        self.assertEquals(updated.featured_queue.state,
                updated.featured_queue.IN_QUEUE)
        self.assertEquals(len(mail.outbox), 2)

    def test_feature_email(self):
        self.login('supermod')
        url = self.channel.get_url()
        self.post_data(url, {'action': 'email', 'type':'Feature',
            'body': 'body', 'email':'email@address.com'})
        updated = Channel.objects.get(pk=self.channel.pk)
        self.assertEquals(updated.state, Channel.NEW)
        self.assertEquals(updated.featured_queue.state,
                updated.featured_queue.IN_QUEUE)
        self.assertEquals(len(mail.outbox), 1)
        self.assertEquals(updated.featured_emails.count(), 1)

    def test_shared_page(self):
        self.login(self.joe)
        self.channel.toggle_moderator_share(self.joe)
        url = reverse('channelguide.moderate.views.shared')
        page = self.get_page(url)
        self.assertEquals(page.context['page'].paginator.count, 1)
        self.assertEquals(page.context['page'].object_list[0], self.channel)

    def test_moderator_history(self):
        admin = self.make_user('admin')
        admin.is_superuser = True
        admin.save()
        self.channel.change_state(self.joe, Channel.DONT_KNOW)
        self.channel.change_state(self.supermod, Channel.APPROVED)
        self.channel.change_state(admin, Channel.REJECTED)

        url = reverse('channelguide.moderate.views.history')
        self.assertLoginRedirect(url)
        self.assertLoginRedirect(url, self.ralph) # user
        self.assertLoginRedirect(url, self.joe) # moderator
        self.assertLoginRedirect(url, self.supermod) # supermod

        page = self.get_page(url, login_as=admin)
        self.assertEquals(page.context['page'].paginator.count, 3)
        object_list = page.context['page'].object_list
        self.assertEquals(object_list[0].action, Channel.REJECTED)
        self.assertEquals(object_list[0].user, admin)
        self.assertEquals(object_list[1].action, Channel.APPROVED)
        self.assertEquals(object_list[1].user, self.supermod)
        self.assertEquals(object_list[2].action, Channel.DONT_KNOW)
        self.assertEquals(object_list[2].user, self.joe)
