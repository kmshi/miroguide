from django import newforms as forms
from django.newforms.forms import NON_FIELD_ERRORS, BoundField

class Form(forms.Form):
    def __init__(self, connection, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        self.connection = connection
        for field in self.fields.values():
            field.connection = connection

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
