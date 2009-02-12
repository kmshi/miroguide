# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

"""Helper utilities that change the django's behaviour."""

from django import forms
from django.utils.translation import gettext as _

class WideMixin(object):
    def widget_attrs(self, widget):
        attrs = super(WideMixin, self).widget_attrs(widget)
        if attrs is None: 
            attrs = {}
        attrs['class'] = 'wide-field'
        return attrs

class WideCharField(WideMixin, forms.CharField):
    def clean(self, value):
        if isinstance(value, unicode):
            if self.max_length is not None and len(value.encode('utf8')) > self.max_length:
                raise forms.ValidationError(_('Ensure this value has at most %(maximum)d bytes (it has %(length)d).') % {'maximum':self.max_length,
                    'length': len(value.encode('utf8'))})
        return super(WideCharField, self).clean(value)

class WideURLField(WideMixin, forms.URLField):
    pass
class WideChoiceField(WideMixin, forms.ChoiceField):
    pass
class WideEmailField(WideMixin, forms.EmailField):
    pass
