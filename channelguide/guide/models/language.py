
# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from channelguide import util
from channelguide.guide import tables
from sqlhelper.orm import Record

class Language(Record):
    """Languages are names for the different languages a channel can be in.
    NOTE: we purposely don't associate languages with ISO codes.  ISO codes
    are for written language, which is distinct from spoken language.
    (for example: Mandarin and Cantonese).
    """
    table = tables.language

    def __init__(self, name=None):
        self.name = name

    def get_absolute_url(self):
        return util.make_absolute_url(self.get_url())

    def get_url(self):
        return util.make_url('languages/%s' % self.name.encode('utf8'),
                             ignore_qmark=True)
    def get_audio_url(self):
        return util.make_url('audio/languages/%s' % self.name.encode('utf8'),
                             ignore_qmark=True)

    def get_rss_url(self):
        return util.make_url('feeds/languages/%s' % self.name,
                             ignore_qmark=True)

    def link(self):
        return util.make_link(self.get_url(), _(self.name))

    def audio_link(self):
        return util.make_link(self.get_audio_url(), _(self.name))

    def __str__(self):
        return self.name

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.name)
