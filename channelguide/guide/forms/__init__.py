import feedparser
import urllib2

from django import newforms as forms
from django.utils.translation import gettext as _

from channelguide.guide.models import User, Channel
from channelguide.guide.feedutil import to_utf8
from fields import WideCharField
from form import Form
from submitform import SubmitChannelForm, EditChannelForm

class RSSFeedField(WideCharField):
    def clean(self, value):
        url = super(RSSFeedField, self).clean(value)
        url = url.strip()
        if Channel.query(url=url).count(self.connection) > 0:
            msg = _("%s is already a channel in the guide") % url
            raise forms.ValidationError(msg)

        missing_feed_msg = _("We can't find a video feed at that address, "
                "please try again.")
        try:
            stream = urllib2.urlopen(url)
            data = stream.read()
        except:
            raise forms.ValidationError(missing_feed_msg)
        parsed = feedparser.parse(data)
        parsed.url = url
        if not parsed.feed or not parsed.entries:
            raise forms.ValidationError(missing_feed_msg)
        return parsed

class FeedURLForm(Form):
    url = RSSFeedField(label=_("Video Feed URL"))

    def get_feed_data(self):
        data = {}
        parsed = self.clean_data['url']
        data['url'] = parsed.url
        def try_to_get(feed_key):
            try:
                return to_utf8(parsed['feed'][feed_key])
            except KeyError:
                return None
        data['name'] = try_to_get('title')
        data['website_url'] = try_to_get('link')
        data['publisher'] = try_to_get('publisher')
        data['short_description'] = try_to_get('description')
        try:
            data['thumbnail_url'] = to_utf8(parsed['feed'].image.href)
        except AttributeError:
            data['thumbnail_url'] = None
        return data
