# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django import newforms as forms
from django.utils.translation import gettext as _

from fields import WideCharField
from form import Form
from channelguide import util
from channelguide.guide import emailmessages
from channelguide.guide.models import User, Channel

class EmailChannelOwnersForm(Form):
    title = WideCharField(max_length=200, label=_("title"))
    body = WideCharField(widget=forms.Textarea, label=_('Body'))

    def send_email(self, sender):
        query = User.query().join('channels')
        query.where(User.c.email.is_not(None))
        query.where(query.joins['channels'].c.state == Channel.APPROVED)
        query.where(channel_owner_emails=True)
        for owner in query.execute(self.connection):
            message = emailmessages.ChannelOwnersEmail(owner,
                self.cleaned_data['title'], self.cleaned_data['body'])
            message.send_email(email_from=sender.email)

