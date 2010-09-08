# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django.db import models

class Cobranding(models.Model):
    user = models.OneToOneField('auth.User', to_field='username',
                                db_column='name', primary_key=True)
    html_title = models.CharField(max_length=100)
    page_title = models.CharField(max_length=100)
    url = models.URLField(max_length=100)
    icon_url = models.URLField(max_length=100, blank=True, null=True)
    favicon_url = models.URLField(max_length=100, blank=True, null=True)
    css_url = models.URLField(max_length=100, blank=True, null=True)
    description = models.TextField()
    link1_url = models.URLField(max_length=100, blank=True, null=True)
    link1_text = models.CharField(max_length=100, blank=True, null=True)
    link2_url = models.URLField(max_length=100, blank=True, null=True)
    link2_text = models.CharField(max_length=100, blank=True, null=True)
    link3_url = models.URLField(max_length=100, blank=True, null=True)
    link3_text = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'cg_cobranding'

    @models.permalink
    def get_url(self):
        return ('channelguide.cobranding.views.cobranding',
                (self.user.username,))

    @models.permalink
    def get_admin_url(self):
        return ('channelguide.cobranding.views.admin',
                (self.user.username,))
