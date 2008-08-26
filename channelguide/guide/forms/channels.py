# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

"""submitform.py.  Channel submission form.  This is fairly complicated, so
it's split off into its own module.  """

from urlparse import urljoin, urlparse
import logging
import os
import tempfile
import urllib2
import socket # for socket.error

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
import django.newforms as forms
import feedparser

from channelguide.guide.feedutil import to_utf8
from channelguide.guide.models import Language, Category, Channel
from channelguide import util
from fields import WideCharField, WideURLField, WideChoiceField
from form import Form

HELP_FORMAT = '<strong>%s</strong> %s'
HD_HELP_TEXT = HELP_FORMAT % \
        (_('What is HD?'),
        _("""Material that is roughly 640x480 non-interlaced, and higher, can
        be marked as HD. This basically translates to DVD quality (without a
        lot of ugly compression artifacts) or better. Roughly 80% of the
        material on the channel must meet this criteria for it to be considered
        HD.  Note: you are welcome to have an HD and non-HD version of the same
        channel """))
RSS_HELP_TEXT = ("An RSS feed is what makes a podcast a "
"podcast. It's a special URL that applications like "
"Miro and iTunes check periodically to know when there "
"is a new video for a channel. Video RSS feeds are "
"strongly recommended for Miro.")

class RSSFeedField(WideCharField):
    def clean(self, value):
        url = super(RSSFeedField, self).clean(value)
        if not url and not self.required:
            return None
        url = url.strip()
        if url.startswith('feed:'):
            url = url.replace('feed:', 'http:', 1)
        if self.initial is not None and url == self.initial:
            return None

        if Channel.query(url=url).count(self.connection) > 0:
            msg = _("%s is already a channel in the guide") % url
            raise forms.ValidationError(msg)
        return self.check_missing(url)

    def check_missing(self, url):
        missing_feed_msg = _("We can't find a video feed at that address, "
                "please try again.")
        try:
            stream = urllib2.urlopen(url)
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

class FeedURLForm(Form):
    name = WideCharField(max_length=200, label=_("Channel Name"))
    url = RSSFeedField(label=_("RSS Feed"), required=False,
                       help_text=RSS_HELP_TEXT)

    def clean_name(self):
        value = self.cleaned_data['name']
        if value == self.fields['name'].initial:
            return value
        if Channel.query(name=value).count(self.connection) > 0:
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
        data['name'] = try_to_get('title')
        data['website_url'] = try_to_get('link')
        data['publisher'] = try_to_get('publisher')
        data['description'] = try_to_get('description')
        try:
            data['thumbnail_url'] = to_utf8(parsed['feed'].image.href)
        except AttributeError:
            data['thumbnail_url'] = None
        return data


class DBChoiceField(WideChoiceField):
    def update_choices(self):
        query = self.db_class.query().order_by('name')
        db_objects = query.execute(self.connection)
        choices = [('', '<none>')]
        choices.extend((obj.id, obj.name) for obj in db_objects)
        self.choices = choices

    def clean(self, value):
        value = WideChoiceField.clean(self, value)
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

    def update_choices(self):
        for field, widget in zip(self.fields, self.widget.widgets):
            field.connection = self.connection
            field.update_choices()
            widget.choices = field.choices

    def compress(self, values):
        if not values or values[0] is None:
            raise forms.ValidationError(_(
                "You must at least enter a primary value."))
        return values

class TagField(WideCharField):
    def __init__(self, tag_limit, *args, **kwargs):
        WideCharField.__init__(self, args, **kwargs)
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
        if self.submitted_thumb_path:
            hidden_render = forms.HiddenInput().render(hidden_name,
                    self.submitted_thumb_path)
        else:
            hidden_render = forms.HiddenInput().render(hidden_name, '')
        return file_render + hidden_render

    def value_from_datadict(self, data, files, name):
        hidden_name = self.get_hidden_name(name)
        if data.get(name):
            return data.get(name)['content']
        elif data.get(hidden_name):
            path = os.path.join(settings.MEDIA_ROOT, 'tmp',
                    data.get(hidden_name))
            return util.read_file(path)
        else:
            return None

    def get_url(self):
        if self.submitted_thumb_path is None:
            return None
        else:
            return urljoin(settings.MEDIA_URL,
                'tmp/%s' % self.submitted_thumb_path_resized())

    def save_submitted_thumbnail(self, data, name):
        hidden_name = self.get_hidden_name(name)
        if data.get(name):
            self.save_thumb_content(data[name]['filename'],
                    data[name]['content'])
        elif data.get(hidden_name):
            self.submitted_thumb_path = data[hidden_name]

    def save_thumb_content(self, filename, content):
        ext = os.path.splitext(filename)[1]
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'tmp')
        util.ensure_dir_exists(temp_dir)
        fd, path = tempfile.mkstemp(prefix='', dir=temp_dir, suffix=ext)
        os.close(fd)
        util.write_file(path, content)
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

class ChannelThumbnailField(forms.Field):

    widget = ChannelThumbnailWidget

    def clean(self, value):
        if not value:
            if self.required:
                raise forms.ValidationError('This field is required.')
            return None
        try:
            ext = util.get_image_extension(value)
        except ValueError:
            raise forms.ValidationError('Not a valid image')
        else:
            if not ext:
                raise forms.ValidationError('Not an image in a format we support.')
            return value

def try_to_download_thumb(url):
    try:
        return urllib2.urlopen(url).read()
    except (urllib2.URLError, ValueError, socket.error):
        return None

class SubmitChannelForm(Form):
    name = WideCharField(max_length=200, label=_("Channel Name"))
    url = RSSFeedField(label=_("RSS Feed"), max_length=200,
                      help_text=RSS_HELP_TEXT, required=False)
    website_url = WideURLField(label=_('Website URL'), max_length=200)
    description = WideCharField(widget=forms.Textarea,
            label=_("Full Description"))
    publisher = forms.EmailField(label=_("Publisher E-mail"), max_length=100)
    tags = TagField(tag_limit=75, required=False,
            label=_('Tags'),
            help_text=_('Keywords that describe this channel.  Separate each '
                'tag with a comma.'))
    categories = TripletField(CategoriesField, label=_("Categories"))
    languages = TripletField(LanguageField, label=_("Languages"),
            help_text=_("What language are most of these videos in?"))
    postal_code = WideCharField(max_length=15, label=_("Postal Code"),
            required=False)
    hi_def = forms.BooleanField(label=_('High Definition'),
            help_text=HD_HELP_TEXT, required=False)
    thumbnail_file = ChannelThumbnailField(label=_('Upload Image'),
                                           help_text="Remember that creating "
                                           "a good channel thumbnail is one of "
                                           "the most important ways to attract "
                                           "new viewers.  It's worth making an "
                                           "effort to do something beautiful.  "
                                           "You can also update the image after"
                                           " you submit your channel.")

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)
        self.set_image_from_feed = False
        self.fields['languages'].update_choices()
        self.fields['categories'].update_choices()

    def clean_website_url(self):
        value = self.cleaned_data['website_url']
        if self.cleaned_data.get('url'):
            return value
        if value == self.fields['website_url'].initial:
            return value
        if Channel.query(website_url=value).count(self.connection) > 0:
            raise forms.ValidationError('That streaming site already exists.')
        return value

    def set_defaults(self, saved_data):
        for key in ('name', 'website_url', 'publisher', 'description'):
            if saved_data.get(key) is not None:
                self.fields[key].initial = saved_data[key]
        if saved_data.get('thumbnail_url'):
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
        channel.join('categories').execute(self.connection)
        channel.categories.clear(self.connection)
        ids = self.cleaned_data['categories']
        if not ids:
            return
        query = Category.query(Category.c.id.in_(ids))
        categories = query.execute(self.connection)
        channel.categories.add_records(self.connection, categories)

    def add_languages(self, channel):
        channel.primary_language_id = self.cleaned_data['languages'][0]
        channel.join("secondary_languages").execute(self.connection)
        channel.secondary_languages.clear(self.connection)
        ids = self.cleaned_data['languages'][1:]
        ids = [id for id in ids if id != channel.primary_language_id]
        if not ids:
            return
        query = Language.query(Language.c.id.in_(ids))
        languages = query.execute(self.connection)
        channel.secondary_languages.add_records(self.connection, languages)

    def add_tags(self, channel):
        tags = self.cleaned_data['tags']
        channel.join('tags', 'owner').execute(self.connection)
        for tag in channel.tags:
            if tag.name not in tags:
                channel.delete_tag(self.connection, channel.owner, tag.name)
        channel.add_tags(self.connection, channel.owner, tags)

    def save_channel(self, creator, feed_url):
        if Channel.query().where(
                Channel.c.url==feed_url).count(self.connection):
            raise forms.ValidationError("Feed URL already exists")
        channel = Channel()
        channel.url = feed_url
        channel.owner_id = creator.id
        self.update_channel(channel)
        return channel

    def update_channel(self, channel):
        string_cols = ('name', 'website_url',
                'description', 'publisher', 'postal_code')
        for attr in string_cols:
            setattr(channel, attr, self.cleaned_data[attr].encode('utf-8'))
        channel.hi_def = self.cleaned_data['hi_def']
        channel.primary_language_id = int(self.cleaned_data['languages'][0])
        channel.save(self.connection)
        self.add_tags(channel)
        self.add_categories(channel)
        self.add_languages(channel)
        if self.cleaned_data['thumbnail_file']:
            channel.save_thumbnail(self.connection,
                    self.cleaned_data['thumbnail_file'])
        channel.update_search_data(self.connection)

    def save_submitted_thumbnail(self):
        thumb_widget = self.fields['thumbnail_file'].widget
        thumb_widget.save_submitted_thumbnail(self.data, 'thumbnail_file')

    def user_uploaded_file(self):
        return self.data.get('thumbnail_file') is not None

class EditChannelForm(FeedURLForm, SubmitChannelForm):

    def __init__(self, request, channel, data=None):
        # django hack to get fields to work right with subclassing
        #self.base_fields = SubmitChannelForm.base_fields

        super(EditChannelForm, self).__init__(request.connection, data)
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
        join = self.channel.join('language', 'secondary_languages',
                'categories')
        join.execute(self.connection)
        for key in ('url', 'name', 'hi_def', 'website_url',
                'description', 'publisher',
                'postal_code'):
            self.fields[key].initial = getattr(self.channel, key)
        tags = self.channel.get_tags_for_owner(self.connection)
        tag_names = [tag.name for tag in tags]
        self.fields['tags'].initial = ', '.join(tag_names)
        self.fields['categories'].initial = [c.id for c in self.channel.categories]
        self.fields['languages'].initial = [self.channel.primary_language_id] +\
                [l.id for l in self.channel.secondary_languages]

    def update_channel(self, channel):
        if self.cleaned_data['url'] is not None:
            channel.url = self.cleaned_data['url'].url
        super(EditChannelForm, self).update_channel(channel)

class FeaturedEmailForm(Form):

    email = forms.EmailField(max_length=50, label=_("Email"))
    title = forms.CharField(max_length=50, label=_("Title"))
    body = forms.CharField(widget=forms.Textarea, label=_("Body"))

    def __init__(self, request, channel, data=None):
        Form.__init__(self, request.connection, data)
        self.channel = channel.join('owner').execute(request.connection)
        self.fields['email'].initial = channel.owner.email
        self.fields['title'].initial = ('%s featured on Miro Guide'
                % channel.name)
        if request.user.fname:
            if request.user.lname:
                name = "%s %s (%s)" % (request.user.fname, request.user.lname,
                        request.user.username)
            else:
                name = "%s (%s)" % (request.user.fname, request.user.username)
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
        self.email = self.cleaned_data['email']
        self.title = self.cleaned_data['title']
        self.body = self.cleaned_data['body']
        util.send_mail(self.title, self.body, [self.email])
