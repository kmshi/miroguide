"""Helper utilities that change the django's behaviour."""

from django import shortcuts
from django import newforms as forms
from django.newforms.forms import NON_FIELD_ERRORS, BoundField
from django.conf import settings
from django.template import RequestContext
from django.utils.translation import gettext as _

def render_to_response(request, template_name, context=None, **kwargs):
    """channel guide version of render_to_response.  It passes the template a
    RequestContext object instead of the standard Context object.  
    """
    return shortcuts.render_to_response(template_name, context,
            context_instance=RequestContext(request), **kwargs)

def context_processor(request):
    """Channelguide context processor.  These attributes get added to every
    template context.
    """

    return {
            'BASE_URL': settings.BASE_URL,
            'request': request,
            'user': request.user,
        }

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

class Form(forms.Form):
    def __init__(self, db_session, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        self.db_session = db_session
        for field in self.fields.values():
            field.db_session = db_session

    def error_list(self):
        for key, error_list in self.errors.items():
            for error in error_list:
                error_info = {'message': error }
                if key != NON_FIELD_ERRORS:
                    bf = BoundField(self, self.fields[key], key)
                    error_info['name'] = bf.label
                else:
                    error_info['name'] = None
                yield error_info

    def field_list(self):
        for field in self:
            if not field.is_hidden:
                yield field

    def hidden_field_list(self):
        for field in self:
            if field.is_hidden:
                yield field
