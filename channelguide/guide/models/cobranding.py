# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from sqlhelper.orm import Record
from channelguide.guide import tables

class Cobranding(Record):
    table = tables.cobranding

    def get_url(self):
        return u'/cobranding/%s' % self.name

    def get_admin_url(self):
        return u'/cobranding/admin/%s' % self.name
