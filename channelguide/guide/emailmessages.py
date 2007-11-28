"""emails.py has the classes that contain the text of the emails we send out.
The main point of this module is to store the text in 1 place.
"""

import urllib
from datetime import datetime, timedelta

from django.conf import settings

from channelguide import util

class EmailMessage(object):
    def __init__(self, title, body):
        self.title = '[Miro Guide] ' + title
        self.body = self.merge_body(body)

    def merge_body(self, body):
        paragraps = body.split('\n\n')
        paragraps = [p.replace('\n', ' ') for p in paragraps]
        return '\n\n'.join(paragraps)

    def send_email(self, recipients, email_from=None, break_lines=True):
        util.send_mail(self.title, self.body, recipients, email_from,
                 break_lines)

class ForgotPasswordEmail(EmailMessage):
    def __init__(self, change_password_url, user):
        EmailMessage.__init__(self, "Forgot Password", """\
To set a new password for your Miro Guide account '%s' click here:

%s.""" % (user.username, change_password_url))

class ChannelOwnersEmail(EmailMessage):
    def __init__(self, owner, title, body):
        self.owner = owner
        EmailMessage.__init__(self, title, body + """\


**Why Did We Contact You?**
You received this message because you have a video feed in the Miro Guide:
(%s) We only send email when there are new features or important updates to
the Guide.

**Unsubscribe Info**
You can change your subscription settings in your user profile: (%s)
""" % (owner.channels[0].get_absolute_url(), owner.get_absolute_url()))

    def send_email(self, email_from):
        EmailMessage.send_email(self, self.owner.email, email_from)

class ChannelNoteEmail(EmailMessage):
    def __init__(self, note):
        EmailMessage.__init__(self, 
                'Note for %s' % note.channel.name, """\
A moderator of the Miro Guide added the following note to your channel:

%s

%s

You may review and respond to the note here: %s""" % \
            (note.title, note.body, note.channel.get_absolute_url()))

class ApprovalEmail(EmailMessage):
    def __init__(self, channel, owner):
        self.channel = channel
        EmailMessage.__init__(self, '%s was approved!' % channel.name, """\
%s,

Your video feed was approved as a channel in the Miro Guide!

You can view your channel here: %s.

If you'd like more viewers to experience your show in Miro, add a 1-click
subscribe button to your web site or myspace page. Then it becomes so easy for
people to get *every* episode of your show: http://subscribe.getmiro.com/

Thanks for adding your show to the Miro Guide.""" % \
        (owner, channel.get_absolute_url()))

    def send_email(self, email_from=None):
        EmailMessage.send_email(self, self.channel.owner.email, email_from)

class RejectionEmail(EmailMessage):
    def __init__(self, channel, header_text, body):
        EmailMessage.__init__(self, '%s was not approved' % channel.name,
                '%s\n\n%s\n' % (self.make_header(header_text), body))

    def make_header(self, text):
        text = ' %s ' % text
        left = '-' * ((50 - len(text)) / 2)
        right = '-' * ((51 - len(text)) / 2)
        return left + text + right

class BrokenChannelEmail(RejectionEmail):
    def __init__(self, channel):
        feedvalidator_link = 'http://feedvalidator.org/check.cgi?url='
        feedvalidator_link += urllib.quote_plus(channel.url)
        RejectionEmail.__init__(self, channel, 'BROKEN', """\
Your feed doesn't seem to work in Miro. You should add your channel into
Miro for yourself to test whether it works or not.  This can easily be done by:
       1. copy your feed
       2. go to the Channels menu, and selecting "Add Channel."

You can also try and see what's wrong by testing it in feedvalidator.org (%s).
If you're having problems finding the problem, please search the Miro forums
(%s) and post a question if you don't find an answer.

Also keep in mind that Miro does not support Shockwave (.swf) files; it does
support Flash video (.flv) files.

Once you have your feed working in Miro, please post a message for us on
the channel page (%s).""" % (feedvalidator_link, settings.FORUMS_URL,
    channel.get_absolute_url()))

class CopyrightViolationEmail(RejectionEmail):
    def __init__(self, channel):
        RejectionEmail.__init__(self, channel, 'COPYRIGHT ISSUES', """\
It appears that your feed might have copyrighted material in it. Due to
the nature of US copyright laws, we cannot feature it in the Miro Guide.

If we are incorrect in supposing that the material was not cleared for
copyright, please contact us at channels@pculture.org""")

class ExplicitContentEmail(RejectionEmail):
    def __init__(self, channel):
        RejectionEmail.__init__(self, channel, 'EXPLICIT CONTENT', """\
Currently, we don't have an user controllable filtering system in place
and cannot accept feeds that are more than "R Rated".""")

class NoVideoEmail(RejectionEmail):
    def __init__(self, channel):
        RejectionEmail.__init__(self, channel, 'NO VIDEO', """\
Your feed is missing video files (it is either empty or consists of
audio only). We require there to be at least 30%% video in a feed for it
to be publishable on the Miro Guide (we're primarily a video
application, after all).

Once you have adequate video in your feed, please post a message 
for us on the channel page (%s), and we'll work on getting it
approved.""" % channel.get_absolute_url())

class ModeratorBoardEmail(EmailMessage):
    def __init__(self, post):
        self.title = '[Miro Guide Moderators] ' + post.title
        board_url = settings.BASE_URL_FULL + 'notes/moderator-board'
        self.body = """\
%s


To send messages to other moderators, go to the moderator message board:
%s """ % (post.body, board_url)

class TroubleshootChannelEmail(EmailMessage):
    def __init__(self, channel, title, body, middle, bottom):
        self.title = '[Miro Guide] %s has been %s' % (channel.name, title)
        feedvalidator_link = 'http://feedvalidator.org/check.cgi?url='
        feedvalidator_link += urllib.quote_plus(channel.url)
        self.body = """%s


*Troubleshooting Your Feed*
%s
Does it work in a browser: %s

Does it validate: %s

Miro Forums: http://www.getmiro.com/forum/categories.php
%s
Note: You can communicate with Miro Guide moderators by using the message system at the bottom of your channel's page in the Miro Guide.""" % (body, middle, channel.url, feedvalidator_link, bottom)

class SuspendedChannelEmail(TroubleshootChannelEmail):
    def __init__(self, channel):
        tenDays = (datetime.now() + timedelta(days=10)).date()
        TroubleshootChannelEmail.__init__(self, channel, 'suspended', """
For some reason, your feed isn't working in Miro. We have temporarily taken it off the Miro Guide and will continue to test it until %s.  If your feed doesn't work by then, you will receive another message.""" % tenDays, """
Check up on your channel here: %s
""" % channel.get_absolute_url(), "")

class RejectedChannelEmail(TroubleshootChannelEmail):
    def __init__(self, channel):
        TroubleshootChannelEmail.__init__(self, channel, 'rejected', """
Your previously working feed has been broken for the past two weeks, therefore we have removed it from being listed in the Miro Guide. If you would like to get your channel re-listed, please get your feed working in Miro and then use the form at the bottom of your channel to get in touch with our moderators (link below).""",
"", """
Once it's fixed, get in touch with us: %s
""" % channel.get_absolute_url())
