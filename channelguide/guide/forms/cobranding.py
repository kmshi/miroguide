from django import newforms as forms
from django.utils.translation import gettext as _

from channelguide.guide.models import Cobranding
from form import Form

class CobrandingAdminForm(Form):
    long_title = forms.CharField(max_length=100, label=_("In-Guide Title"))
    short_title = forms.CharField(max_length=30, label=_("Sidebar Title"))
    url = forms.CharField(max_length=100, label=_("URL"))
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
        for name in ('long_title', 'short_title', 'url', 'description'):
            if self.cleaned_data.get(name) is not None:
                setattr(self.cobrand, name, self.cleaned_data[name])
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
