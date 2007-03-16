"""submitform.py.  Channel submission form.  This is fairly complicated, so
it's split off into its own module.
"""

from urlparse import urljoin, urlparse
import os
import tempfile
import urllib2

from django.conf import settings
import django.newforms as forms
from django.newforms.forms import BoundField

from channelguide import util
from channelguide.guide.models import Language, Category, Channel
from fields import WideCharField, WideURLField, WideChoiceField
from form import Form

class DBChoiceField(WideChoiceField):
    def update_choices(self):
        q = self.db_session.query(self.db_class)
        db_objects = q.select(order_by=self.db_class.c.name)
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
        return urljoin(settings.MEDIA_URL, 
                'tmp/%s' % self.submitted_thumb_path)

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
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        fd, path = tempfile.mkstemp(prefix='', dir=temp_dir, suffix=ext)
        os.close(fd)
        util.write_file(path, content)
        self.submitted_thumb_path = os.path.basename(path)

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
    thumbnail_file = forms.Field(widget=ChannelThumbnailWidget, 
            label=_('Upload Channel Thumbnail'))

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
                widget.save_thumb_content(url_path, content)
                self.set_image_from_feed = True

    def get_template_data(self):
        return { 
            'form': self, 
            'submitted_thumb_url':
                self.fields['thumbnail_file'].widget.get_url(),
        }

    def add_mapped_objects(self, class_, collection, keys,
            ignore_ids=None):
        if ignore_ids is None:
            ignore_ids = []
        already_added = set(ignore_ids)
        for name in keys:
            id = self.clean_data[name]
            if id is None:
                continue
            id = int(id)
            if id not in already_added:
                obj = self.db_session.get(class_, id)
                collection.append(obj)
                already_added.add(id)

    def add_categories(self, channel):
        self.add_mapped_objects(Category, channel.categories,
                ('category1', 'category2', 'category3'))

    def add_languages(self, channel):
        channel.primary_language_id = int(self.clean_data['language'])
        self.add_mapped_objects(Language,
                channel.secondary_languages, ('language2', 'language3'),
                ignore_ids=[channel.primary_language_id])

    def save_channel(self, creator, feed_url):
        channel = Channel()
        simple_cols = ('name', 'website_url', 'short_description',
                'description', 'publisher', 'hi_def')
        for attr in simple_cols:
            setattr(channel, attr, self.clean_data[attr])
        channel.url = feed_url
        channel.owner = creator
        if self.clean_data['tags']:
            channel.add_tags(creator, self.clean_data['tags'])
        self.add_categories(channel)
        self.add_languages(channel)
        self.db_session.save(channel)
        self.db_session.flush()
        if self.clean_data['thumbnail_file']:
            channel.save_thumbnail(self.clean_data['thumbnail_file'])
        channel.refresh_search_data()
        return channel

    def save_submitted_thumbnail(self):
        thumb_widget = self.fields['thumbnail_file'].widget
        thumb_widget.save_submitted_thumbnail(self.data, 'thumbnail_file')

    def user_uploaded_file(self):
        return self.data.get('thumbnail_file') is not None
