"""Helper utilities that change the django's behaviour."""

from django import newforms as forms

class WideMixin(object):
    def widget_attrs(self, widget):
        attrs = super(WideMixin, self).widget_attrs(widget)
        if attrs is None: 
            attrs = {}
        attrs['class'] = 'wide-field'
        return attrs

class WideCharField(WideMixin, forms.CharField):
    pass
class WideURLField(WideMixin, forms.URLField):
    pass
class WideChoiceField(WideMixin, forms.ChoiceField):
    pass
