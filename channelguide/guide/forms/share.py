# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django import newforms as forms
from django.utils.translation import ugettext as _

SHARE_TYPES = (('feed', 'feed'),
               ('item', 'item'))


class ShareForm(forms.Form):
    share_type = forms.ChoiceField(choices=SHARE_TYPES)
    from_email = forms.EmailField()
    recipients = forms.CharField()
    comment = forms.CharField(required=False)
    feed_url = forms.URLField(required=False)
    file_url = forms.URLField(required=False)
    item_name = forms.CharField(required=False)

    def clean_recipients(self):
        cleaned_recipients = []
        for recipient in self.cleaned_data['recipients'].split(','):
            recipient = recipient.strip()
            if not forms.fields.email_re.match(recipient):
                raise forms.ValidationError(
                    _(u'"Recipients" field must be a comma '
                      u'separated list of email addresses'))
            cleaned_recipients = recipient

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
