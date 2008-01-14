from django import newforms as forms
from django.utils.translation import gettext as _

from channelguide.guide.models import Cobranding
from form import Form

class CobrandingAdminForm(Form):
    html_title = forms.CharField(max_length=100, label=_("Title in Miro App"),
            help_text=_("This is the title that will appear in the sidebar of Miro."))
    page_title = forms.CharField(max_length=30, label=_("Page Title"),
            help_text=_("This is the title that will be displayed at the top of the page."))
    url = forms.CharField(max_length=100, label=_("Website URL"))
    icon_url = forms.CharField(required=False, max_length=100,
            label=_("Icon URL"), help_text=_("Icon should be 175x125 pixels."))
    favicon_url = forms.CharField(required=False, max_length=100,
            label=_("Favicon URL"))
    description = forms.CharField(widget=forms.Textarea, label=_("Description"))
    link1_url = forms.CharField(required=False, max_length=100,
            label=_("Link 1 URL"), help_text=_("Or leave this blank to have plain text.  All these links are optional."))
    link1_text = forms.CharField(required=False, max_length=100,
            label=_("Link 1 Text"))
    link2_url = forms.CharField(required=False, max_length=100,
            label=_("Link 2 URL"))
    link2_text = forms.CharField(required=False, max_length=100,
            label=_("Link 2 Text"))
    link3_url = forms.CharField(required=False, max_length=100,
            label=_("Link 3 URL"))
    link3_text = forms.CharField(required=False, max_length=100,
            label=_("Link 3 Text"))

    def __init__(self, connection, cobrand, data=None):
        super(CobrandingAdminForm, self).__init__(connection, data)
        self.cobrand = cobrand
        self.set_defaults()

    def set_defaults(self):
        for name, field in self.fields.items():
            field.initial = getattr(self.cobrand, name)

    def update_cobrand(self):
        for name in ('html_title', 'page_title', 'url', 'description'):
            if self.cleaned_data.get(name) is not None:
                setattr(self.cobrand, name, self.cleaned_data[name])
        for name in ('icon_url', 'favicon_url'):
            icon_url = self.cleaned_data.get(name)
            if icon_url is not None:
                if icon_url == u'':
                    setattr(self.cobrand, name, None)
                else:
                    setattr(self.cobrand, name, icon_url)
        for i in range(1, 4):
            for suffix in ('url', 'text'):
                name = 'link%i_%s' % (i, suffix)
                value = self.cleaned_data.get(name)
                if value is not None:
                    if value == u'':
                        setattr(self.cobrand, name, None)
                    else:
                        setattr(self.cobrand, name, value)
        self.cobrand.save(self.connection)
