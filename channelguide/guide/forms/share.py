# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

import urlparse

from django import forms
from django.conf import settings
from django.utils.translation import ugettext as _

SHARE_TYPES = (('feed', 'feed'),
               ('item', 'item'))


class ShareForm(forms.Form):
    share_type = forms.ChoiceField(choices=SHARE_TYPES)
    from_email = forms.EmailField()
    recipients = forms.CharField()
    share_url = forms.URLField()
    comment = forms.CharField(required=False)
    feed_url = forms.URLField(required=False)
    file_url = forms.URLField(required=False)
    item_name = forms.CharField(required=False)

    def clean_share_url(self):
        share_url = self.cleaned_data['share_url']

        share_url_path = urlparse.urlsplit(share_url)[2]

        if not share_url.startswith(settings.BASE_URL_FULL):
            raise forms.ValidationError(
                u'This URL does not look like it belongs to this site')

        if (self.cleaned_data['share_type'] == 'feed'
            and not (share_url_path.startswith('/feeds/')
                     or share_url_path.startswith('/share/feed/'))):
            raise forms.ValidationError(
                u'Not a valid share_url for this share_type')
        elif (self.cleaned_data['share_type'] == 'item'
              and not (share_url_path.startswith('/items/')
                       or share_url_path.startswith('/share/item/'))):
            raise forms.ValidationError(
                u'Not a valid share_url for this share_type')

        return share_url

    def clean_recipients(self):
        cleaned_recipients = []
        for recipient in self.cleaned_data['recipients'].split(','):
            recipient = recipient.strip()
            if not forms.fields.email_re.match(recipient):
                raise forms.ValidationError(
                    _(u'"Recipients" field must be a comma '
                      u'separated list of email addresses'))
            cleaned_recipients.append(recipient)

        return cleaned_recipients
    
    def clean_feed_url(self):
        share_type = self.cleaned_data.get('share_type')
        feed_url = self.cleaned_data.get('feed_url')

        if share_type == 'feed' and not feed_url:
            raise forms.ValidationError(
                _(u"feed_url not provided despite share_type being "
                  u"set to 'feed'"))

        return feed_url

    def clean_file_url(self):
        share_type = self.cleaned_data.get('share_type')
        file_url = self.cleaned_data.get('file_url')

        if share_type == 'item' and not file_url:
            raise forms.ValidationError(
                _(u"file_url not provided despite share_type being "
                  u"set to 'item'"))

        return file_url

    def get_share_url(self):
        pass
