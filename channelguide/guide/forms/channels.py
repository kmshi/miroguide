"""submitform.py.  Channel submission form.  This is fairly complicated, so
it's split off into its own module.  """

from urlparse import urljoin, urlparse
import logging
import os
import tempfile
import urllib2

from django.conf import settings
from django.newforms.forms import BoundField
from django.utils.translation import gettext as _
import django.newforms as forms
import feedparser

from channelguide.guide.feedutil import to_utf8
from channelguide.guide.models import Language, Category, Channel, User
from channelguide import util
from fields import WideCharField, WideURLField, WideChoiceField
from form import Form

class RSSFeedField(WideCharField):
    def clean(self, value):
        url = super(RSSFeedField, self).clean(value)
        url = url.strip()
        if url.startswith('feed:'):
            url = url.replace('feed:', 'http:', 1)
        if url != self.initial:
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
        parsed = self.cleaned_data['url']
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

class TagField(WideCharField):
    def __init__(self, tag_limit, *args, **kwargs):
        WideCharField.__init__(self, args, **kwargs)
        self.tag_limit = tag_limit

    def clean(self, value):
        if value is None or value.strip() == '':
            return []
        value = value.strip()
        tags = [t.strip() for t in value.split(',') if t.strip() != '']
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

    def value_from_datadict(self, data, name):
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

def try_to_download_thumb(url):
    try:
        return urllib2.urlopen(url).read()
    except urllib2.URLError, ValueError:
        return None

class SubmitChannelForm(Form):
    name = WideCharField(max_length=200, label=_("Channel Name"))
    website_url = WideURLField(label=_('Website URL'))
    short_description = WideCharField()
    description = WideCharField(widget=forms.Textarea, 
            label=_("Full Description"))
    publisher = WideCharField(max_length=100)
    language = LanguageField(label=_("Primary Language"),
            help_text=_("What language are most of these videos in?"))
    language2 = LanguageField(label=_("Additional Language"), 
            help_text=_('Are some of these videos in an additional '
                        'language?'),
            required=False)
    language3 = LanguageField(label=_("Additional Language"), 
            help_text=_('Are some of these videos in an additional '
                        'language?'),
            required=False)
    category1 = CategoriesField(label=_("Primary Category"),
            help_text=_('Which category best fits this channel?'))
    category2 = CategoriesField(label=_("Additional Category"),
            help_text=_('Is there another category that this channel '
                        'belongs in?'),
            required=False)
    category3 = CategoriesField(label=_("Additional Category"),
            help_text=_('Is there another category that this channel '
                        'belongs in?'),
            required=False)
    tags = TagField(tag_limit=5, required=False,
            label=_('Tags (up to 5)'),
            help_text=_('Keywords that describe this channel.  Separate each '
                'tag with a comma.'))
    hi_def = forms.BooleanField(label=_('High Definition'), 
            help_text=_('The videos on this channel are primarily in an HD '
                        'format.'),
            required=False)
    postal_code = WideCharField(max_length=15, label=_("Postal Code"),
            required=False)
    thumbnail_file = forms.Field(widget=ChannelThumbnailWidget, 
            label=_('Upload Image'))

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)
        self.set_image_from_feed = False
        for name in ('category1', 'category2', 'category3',
                'language', 'language2', 'language3'):
            self.fields[name].update_choices()

    def field_list(self):
        for field in super(SubmitChannelForm, self).field_list():
            # thumbnail_file is special cased
            if field.name != 'thumbnail_file': 
                yield field

    def thumbnail_widget(self):
        return BoundField(self, self.fields['thumbnail_file'],
                'thumbnail_file')

    def set_defaults(self, saved_data):
        for key in ('name', 'website_url', 'publisher', 'short_description'):
            if saved_data[key] is not None:
                self.fields[key].initial = saved_data[key]
        if saved_data['thumbnail_url']:
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
        ids = self.get_ids('category1', 'category2', 'category3')
        if not ids:
            return
        query = Category.query(Category.c.id.in_(ids))
        categories = query.execute(self.connection)
        channel.categories.add_records(self.connection, categories)

    def add_languages(self, channel):
        channel.join("secondary_languages").execute(self.connection)
        channel.secondary_languages.clear(self.connection)
        ids = self.get_ids('language2', 'language3')
        ids = [id for id in ids if id != channel.primary_language_id]
        if not ids:
            return
        query = Language.query(Language.c.id.in_(ids))
        languages = query.execute(self.connection)
        channel.secondary_languages.add_records(self.connection, languages)

    def add_tags(self, channel):
        tags = self.cleaned_data['tags']
        if not tags:
            return
        channel.join('tags', 'owner').execute(self.connection)
        for tag in channel.tags:
            if tag.name not in tags:
                channel.delete_tag(self.connection, channel.owner, tag)
        channel.add_tags(self.connection, channel.owner, tags)

    def save_channel(self, creator, feed_url):
        channel = Channel()
        channel.url = feed_url
        channel.owner = creator
        self.update_channel(channel)
        return channel

    def update_channel(self, channel):
        simple_cols = ('name', 'website_url', 'short_description',
                'description', 'publisher', 'hi_def', 'postal_code')
        for attr in simple_cols:
            setattr(channel, attr, self.cleaned_data[attr])
        channel.primary_language_id = int(self.cleaned_data['language'])
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
    def __init__(self, connection, channel, data=None):
        # django hack to get fields to work right with subclassing
        #self.base_fields = SubmitChannelForm.base_fields 

        super(EditChannelForm, self).__init__(connection, data)
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
                'short_description', 'description', 'publisher',
                'postal_code'):
            self.fields[key].initial = getattr(self.channel, key)
        self.fields['language'].initial = self.channel.language.id
        tags = self.channel.get_tags_for_owner(self.connection)
        tag_names = [tag.name for tag in tags]
        self.fields['tags'].initial = ', '.join(tag_names)
        def set_from_list(key, list, index):
            try:
                self.fields[key].initial = list[index].id
            except IndexError:
                pass
        set_from_list('language2', self.channel.secondary_languages, 0)
        set_from_list('language3', self.channel.secondary_languages, 1)
        set_from_list('category1', self.channel.categories, 0)
        set_from_list('category2', self.channel.categories, 1)
        set_from_list('category3', self.channel.categories, 2)

    def update_channel(self, channel):
        channel.url = self.cleaned_data['url'].url
        super(EditChannelForm, self).update_channel(channel)
