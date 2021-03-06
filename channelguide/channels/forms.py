# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

"""submitform.py.  Channel submission form.  This is fairly complicated, so
it's split off into its own module.  """

from urlparse import urljoin, urlparse
import logging
import os
import re
import tempfile

from django.conf import settings
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from django import forms
import feedparser
import ip2cc

from channelguide.guide.feedutil import to_utf8
from channelguide.guide import emailmessages
from channelguide.channels.models import Channel, try_to_download_thumb
from channelguide.labels.models import Language, Category
from channelguide.search.models import ChannelSearchData
from channelguide import util

HD_HELP_TEXT =  _(
    "Only mark your channel as HD if you the video resolution is 1080x720 "
    "or higher. Roughly 95% of the material on the channel should meet this "
    "criteria for it to be considered HD.")
RSS_HELP_TEXT = _('Our <a href="http://getmiro.com/publish/">Publishers '
                  'Guide</a> has details on finding your RSS feed. Chances '
                  'are, you already have one (YouTube, blip.tv, Vimeo, etc. '
                  'all have them).')
UPLOAD_HELP_TEXT = _("This is the single most important part of submitting "
                     "a channel &mdash; a good channel thumbnail is proven to "
                     "attract more viewers. It's worth making an effort to "
                     "do something beautiful. If your channel is featured, it "
                     "will need to have the name of your show in it. You can "
                     "update this image at any time.")

YOUTUBE_USER_URL_RE = re.compile(
    r'http://www.youtube.com/rss/user/([^/]+)/videos.rss')
YOUTUBE_TITLE_RE = re.compile(r'YouTube :: (?P<realtitle>.+)')


class RSSFeedField(forms.CharField):
    def clean(self, value):
        url = super(RSSFeedField, self).clean(value)
        if not url and not self.required:
            return None
        url = url.strip()
        if url.startswith('feed:'):
            url = url.replace('feed:', 'http:', 1)
        if self.initial is not None and url == self.initial:
            return None

        if Channel.objects.filter(url=url).count() > 0:
            msg = _("%s is already a channel in the guide") % url
            raise forms.ValidationError(msg)
        return self.check_missing(url)

    def check_missing(self, url):
        missing_feed_msg = _("We can't find a video feed at that address, "
                "please try again.")
        try:
            stream = util.open_url_while_lying_about_agent(url)
            data = stream.read()
        except:
            raise forms.ValidationError(missing_feed_msg)
        try:
            parsed = feedparser.parse(data)
        except:
            raise forms.ValidationError(missing_feed_msg)
        parsed.url = url
        if not parsed.feed or not parsed.entries:
            raise forms.ValidationError(missing_feed_msg)
        return parsed

class FeedURLForm(forms.Form):
    name = forms.CharField(max_length=200, label=_("Show Name"))
    url = RSSFeedField(label=_("RSS Feed"), required=False,
                       help_text=RSS_HELP_TEXT)

    def __init__(self, *args, **kwargs):
        if kwargs.has_key('url_required'):
            self.base_fields['url'].required = kwargs['url_required']
            kwargs.pop('url_required')
        forms.Form.__init__(self, *args, **kwargs)

    def clean_name(self):
        value = self.cleaned_data['name']
        if value == self.fields['name'].initial:
            return value
        if Channel.objects.filter(name=value).count() > 0:
            raise forms.ValidationError('That channel already exists')
        else:
            return value

    def get_feed_data(self):
        data = {}
        parsed = self.cleaned_data['url']
        data['url'] = parsed.url
        def try_to_get(feed_key):
            try:
                return to_utf8(parsed['feed'][feed_key])
            except (KeyError, TypeError):
                return None
        data['name'] = self.cleaned_data['name']
        data['website_url'] = try_to_get('link')
        match = YOUTUBE_USER_URL_RE.match(data['website_url'])
        if match:
            data['website_url'] = 'http://www.youtube.com/user/%s' % (
                match.groups()[0])
        data['publisher'] = try_to_get('publisher')
        data['description'] = try_to_get('description')
        try:
            data['thumbnail_url'] = to_utf8(parsed['feed'].image.href)
        except AttributeError:
            data['thumbnail_url'] = None

        # Special hack for YouTube titles.
        # It's really a PITA to have to strip out 'YouTube :: ' from
        # the title all the time, and it certainly doesn't look good
        # to have channel names like that in Miro.  So we reverse that
        # and put it at the end.
        youtube_re = YOUTUBE_TITLE_RE.match(data['name'])
        if youtube_re:
            data['name'] = u'%s :: YouTube' % (
                youtube_re.groupdict()['realtitle'])

        return data


class DBChoiceField(forms.ChoiceField):
    def update_choices(self, skip=()):
        db_objects = self.db_class.objects.order_by('name')
        choices = [('', '<none>')]
        choices.extend((obj.id, obj.name) for obj in db_objects
                       if obj.name not in skip)
        self.choices = choices

    def clean(self, value):
        value = forms.ChoiceField.clean(self, value)
        if value == '':
            value = None
        return value

class CategoriesField(DBChoiceField):
    db_class = Category

class LanguageField(DBChoiceField):
    db_class = Language

class TripletWidget(forms.MultiWidget):

    def __init__(self, widget):
        super(TripletWidget, self).__init__((widget, widget, widget))

    def decompress(self, value):
        if value is None:
            return [None, None, None]
        return value

    def render(self, name, value, attrs=None):
        if not value or len(value) < 3:
            self.widgets = self.widgets[:2] # don't display the 3rd option
        return super(TripletWidget, self).render(name, value, attrs)

    def format_output(self, rendered_widgets):
        names = (_("1st"), _("2nd"), _("3rd"))
        context = {'rendered_widgets': zip(names, rendered_widgets),
                'STATIC_BASE_URL': settings.STATIC_BASE_URL }
        return render_to_string('guide/form-field-triplet.html', context)

class TripletField(forms.MultiValueField):

    def __init__(self, field, *args, **kw):
        kw['widget'] = TripletWidget(field.widget)
        kw['required'] = False
        args = ((field(), field(), field()),) + args
        super(TripletField, self).__init__(*args, **kw)

    def update_choices(self, skip=()):
        for field, widget in zip(self.fields, self.widget.widgets):
            field.update_choices(skip=skip)
            widget.choices = field.choices

    def compress(self, values):
        if not values or values[0] is None:
            raise forms.ValidationError(_(
                "You must at least enter a primary value."))
        return values

class TagField(forms.CharField):
    def __init__(self, tag_limit, *args, **kwargs):
        forms.CharField.__init__(self, *args, **kwargs)
        self.tag_limit = tag_limit

    def clean(self, value):
        if value is None or value.strip() == '':
            return []
        tags = []
        for name in value.strip().split(','):
            name = name.strip()
            if name != '':
                tags.append(name)
        if len(tags) > self.tag_limit:
            msg = _('you can only enter up to %d tags.') % self.tag_limit
            raise forms.ValidationError(msg)
        return tags

class ChannelThumbnailWidget(forms.Widget):
    def __init__(self):
        self.submitted_thumb_path = None
        self.attrs = {}

    def get_hidden_name(self, name):
        return name + '_submitted_path'

    def render(self, name, value, attrs=None):
        hidden_name = self.get_hidden_name(name)
        file_render = forms.FileInput().render(name, '')
        if self.submitted_thumb_path is not None:
            hidden_render = forms.HiddenInput().render(hidden_name,
                    self.submitted_thumb_path)
        else:
            hidden_render = forms.HiddenInput().render(hidden_name, '')
        return file_render + hidden_render

    def value_from_datadict(self, data, files, name):
        hidden_name = self.get_hidden_name(name)
        if files.get(name):
            uploaded_file = files[name]
            uploaded_file.open()
            return uploaded_file
        elif data.get(hidden_name):
            path = os.path.join(settings.MEDIA_ROOT, 'tmp',
                    data.get(hidden_name))
            return open(path, 'rb')
        else:
            return None

    def get_url(self):
        if self.submitted_thumb_path is None:
            return None
        else:
            return urljoin(settings.BASE_URL,
                           'media/tmp/%s' %
                           self.submitted_thumb_path_resized())

    def save_submitted_thumbnail(self, data, name):
        hidden_name = self.get_hidden_name(name)
        if data.get(name):
            uploaded_file = data[name]
            uploaded_file.open()
            file_name = uploaded_file.name
            self.save_thumb_content(file_name, uploaded_file)
        elif data.get(hidden_name):
            self.submitted_thumb_path = data[hidden_name]

    def save_thumb_content(self, filename, content_file):
        ext = os.path.splitext(filename)[1]
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'tmp')
        util.ensure_dir_exists(temp_dir)
        fd, path = tempfile.mkstemp(prefix='', dir=temp_dir, suffix=ext)
        os.close(fd)
        content_file.seek(0)
        util.copy_obj(path, content_file)
        self.submitted_thumb_path = os.path.basename(path)
        try:
            self.resize_submitted_thumb()
        except ValueError:
            self.submitted_thumb_path = None
        except:
            self.submitted_thumb_path = None
            raise

    def resize_submitted_thumb(self):
        width, height = Channel.THUMBNAIL_SIZES[-1]
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'tmp')
        source = os.path.join(temp_dir, self.submitted_thumb_path)
        dest = os.path.join(temp_dir, self.submitted_thumb_path_resized())
        util.make_thumbnail(source, dest, width, height)

    def submitted_thumb_path_resized(self):
        path, ext = os.path.splitext(self.submitted_thumb_path)
        return path + '-resized' + ext

class ChannelThumbnailField(forms.FileField):

    widget = ChannelThumbnailWidget

    def clean(self, value, initial):
        if not value:
            if self.required:
                raise forms.ValidationError(_('This field is required.'))
            return None
        try:
            ext = util.get_image_extension(value)
        except ValueError:
            raise forms.ValidationError(_('Not a valid image'))
        else:
            if not ext:
                raise forms.ValidationError(
                    _('Not an image in a format we support.'))
            return value

class SubmitChannelForm(forms.Form):
    name = forms.CharField(max_length=200, label=_("Show Name"))
    url = RSSFeedField(label=_("RSS Feed"), max_length=200,
                      help_text=RSS_HELP_TEXT, required=False)
    website_url = forms.URLField(label=_('Website URL'), max_length=200,
                               help_text=_("Don't forget to add a website URL "
                                           "for the show."))
    description = forms.CharField(widget=forms.Textarea,
            label=_("Full Description"))
    publisher = forms.CharField(label=_("Publisher"), max_length=100,
                                required=False,
                                help_text=_("The person or company "
                                            "responsible for publishing this "
                                            "show."))
    tags = TagField(tag_limit=75, required=False,
                    label=_('Tags'),
                    help_text=_('Separate each tag with a comma.'))
    geoip = forms.CharField(max_length=100, label=_("Geo restrictions"),
                          help_text=_("Use commas to separate two letter "
                                      "country codes. Countries listed here "
                                      "are the ONLY ones that will see this "
                                      "site or show."),
                          required=False)
    categories = TripletField(CategoriesField, label=_("Genres"),
                              help_text=_("Pick at least one genre."))
    language = LanguageField(label=_("Language"),
                             help_text=_("Users can filter their searches by "
                                         "language."))
    #postal_code = WideCharField(max_length=15, label=_("Postal Code"),
    #        required=False)
    hi_def = forms.BooleanField(label=_('High Definition'),
            help_text=HD_HELP_TEXT, required=False)
    thumbnail_file = ChannelThumbnailField(
        label=_('Upload Image (optimal size: 400x267)'),
        help_text=UPLOAD_HELP_TEXT)

    def __init__(self, *args, **kwargs):
        if 'url_required' in kwargs:
            url_required = kwargs.pop('url_required')
        else:
            url_required = False
        forms.Form.__init__(self, *args, **kwargs)
        self.set_image_from_feed = False
        self.fields['language'].update_choices()

        if url_required:
            self.fields['url'].required = url_required
            self.fields['categories'].update_choices(skip=('Courseware',))
        else:
            self.fields['categories'].update_choices()

    def clean_website_url(self):
        value = self.cleaned_data['website_url']
        if self.cleaned_data.get('url'):
            return value
        if value == self.fields['website_url'].initial:
            return value
        if Channel.objects.filter(website_url=value, url=None).count() > 0:
            raise forms.ValidationError(
                _('That streaming site already exists.'))
        return value

    def clean_geoip(self):
        value = self.cleaned_data['geoip'].upper()
        if not value:
            return value
        codes = [code.strip() for code in value.split(',')]
        filtered = [code for code in codes if code not in ip2cc.cc2name]
        if filtered:
            raise forms.ValidationError(
                _('The following country codes are invalid: %s') %
                ', '.join(filtered))
        return ','.join(codes)

    def set_defaults(self, saved_data):
        if saved_data['owner-is-fan']:
            self.fields['publisher'].required = False
        for key in ('name', 'website_url', 'publisher', 'description', 'url',
                    'geoip'):
            if saved_data.get(key) is not None:
                self.fields[key].initial = saved_data[key]
        if not saved_data.get('url'):
            self.fields['geoip'].initial = 'US'
        if saved_data.get('thumbnail_url') and \
                'youtube.com/rss' not in saved_data['url'] and \
                'videobomb.com/rss' not in saved_data['url']:
            content = try_to_download_thumb(saved_data['thumbnail_url'])
            if content:
                widget = self.fields['thumbnail_file'].widget
                url_path = urlparse(saved_data['thumbnail_url'])[2]
                try:
                    widget.save_thumb_content(url_path, content)
                except Exception, e:
                    logging.warn("Couldn't convert image from %s. Error:\n%s",
                            saved_data['thumbnail_url'], e)
                else:
                    self.set_image_from_feed = True

    def get_template_data(self):
        return {
            'form': self,
            'submitted_thumb_url':
                self.fields['thumbnail_file'].widget.get_url(),
        }

    def get_ids(self, *keys):
        ids = set()
        for key in keys:
            value = self.cleaned_data[key]
            if value is not None:
                ids.add(int(value))
        return ids

    def add_categories(self, channel):
        channel.categories.clear()
        ids = self.cleaned_data['categories']
        if not ids:
            return
        categories = Category.objects.filter(pk__in=ids)
        channel.categories = categories

    def add_tags(self, channel):
        tags = self.cleaned_data['tags']
        for tag in channel.tags.all():
            if tag.name not in tags:
                channel.delete_tag(channel.owner, tag.name)
        channel.add_tags(channel.owner, tags)

    def save_channel(self, creator, feed_url):
        if Channel.objects.filter(url=feed_url).count():
            raise forms.ValidationError(_("Feed URL already exists"))
        channel = Channel()
        channel.url = feed_url
        channel.owner = creator
        self.update_channel(channel)
        return channel

    def update_channel(self, channel):
        string_cols = ('name', 'website_url',
                'description', 'publisher', 'geoip')
        for attr in string_cols:
            setattr(channel, attr, unicode(self.cleaned_data[attr]))
        channel.hi_def = self.cleaned_data['hi_def']
        channel.language_id = int(self.cleaned_data['language'])
        channel.save()
        self.add_tags(channel)
        self.add_categories(channel)
        if self.cleaned_data['thumbnail_file']:
            channel.save_thumbnail(
                    self.cleaned_data['thumbnail_file'])
        ChannelSearchData.objects.update(channel)

    def save_submitted_thumbnail(self):
        thumb_widget = self.fields['thumbnail_file'].widget
        thumb_widget.save_submitted_thumbnail(self.files, 'thumbnail_file')

    def user_uploaded_file(self):
        return self.data.get('thumbnail_file') is not None

class EditChannelForm(FeedURLForm, SubmitChannelForm):

    def __init__(self, channel, *args, **kwargs):
        FeedURLForm.__init__(self, *args, **kwargs)
        SubmitChannelForm.__init__(self, *args, **kwargs)
        self.channel = channel
        self.fields['thumbnail_file'].required = False
        self.set_image_from_channel = False
        self.set_initial_values()

    def get_template_data(self):
        data = super(EditChannelForm, self).get_template_data()
        if data['submitted_thumb_url'] is None:
            data['submitted_thumb_url'] = self.channel.thumb_url(370, 247)
            self.set_image_from_channel = True
        return data

    def set_initial_values(self):
        for key in ('url', 'name', 'hi_def', 'website_url',
                'description', 'publisher', 'geoip'):
            self.fields[key].initial = getattr(self.channel, key)
        tags = self.channel.get_tags_for_owner()
        tag_names = [tag.name for tag in tags]
        self.fields['tags'].initial = ', '.join(tag_names)
        self.fields['categories'].initial = [c.id for c in
                                             self.channel.categories.all()]
        self.fields['language'].initial = self.channel.language.pk

    def update_channel(self, channel):
        if self.cleaned_data['url'] is not None:
            channel.url = self.cleaned_data['url'].url
        super(EditChannelForm, self).update_channel(channel)

class EmailChannelOwnersForm(forms.Form):
    title = forms.CharField(max_length=200, label=_("title"))
    body = forms.CharField(widget=forms.Textarea, label=_('Body'))

    def send_email(self, sender):
        for owner in User.objects.exclude(email=None).exclude(email='').filter(
            channels__state=Channel.APPROVED,
            userprofile__channel_owner_emails=True).distinct():
            message = emailmessages.ChannelOwnersEmail(owner,
                self.cleaned_data['title'], self.cleaned_data['body'])
            message.send_email(email_from=sender.email)

