# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.utils.translation import ugettext_lazy as _
from django import forms

from channelguide import util
from channelguide.featured.models import FeaturedEmail

class FeaturedEmailForm(forms.Form):
    email = forms.EmailField(max_length=50, label=_("Email"))
    title = forms.CharField(max_length=50, label=_("Title"))
    body = forms.CharField(widget=forms.Textarea, label=_("Body"))

    def __init__(self, request, channel, data=None):
        forms.Form.__init__(self, data)
        self.channel = channel
        self.sender = request.user
        self.fields['email'].initial = channel.owner.email
        self.fields['title'].initial = ('%s featured on Miro Guide'
                % channel.name)
        if request.user.first_name:
            if request.user.last_name:
                name = "%s %s (%s)" % (request.user.first_name,
                                       request.user.last_name,
                                       request.user.username)
            else:
                name = "%s (%s)" % (request.user.first_name,
                                    request.user.username)
        else:
            name = request.user.username
        self.fields['body'].initial = \
                """Hello,

We want to let you know that %s has been featured on Miro in the Channel Guide. Every week we showcase different podcasts to expose our users to interesting and high quality video feeds. Feel free to take a look and you will see %s scrolling across on the featured channels here:

https://miroguide.com/

If you would like to be able to update the description of your channel(s) and if you do not already have control of your feeds in the Miro Guide, I am happy to help you get set up.

-Regards,
%s

PS. Miro 1-click links rock! They give your viewers a simple way to go directly
from your website to being subscribed to your feed in Miro:
http://subscribe.getmiro.com/
""" % (channel.name, channel.name, name)

    def send_email(self):
        email = self.cleaned_data['email']
        title = self.cleaned_data['title']
        body = self.cleaned_data['body']
        util.send_mail(title, body, [email])
        FeaturedEmail.objects.create(
            channel = self.channel,
            title = title,
            body = body,
            email = email,
            sender = self.sender)

