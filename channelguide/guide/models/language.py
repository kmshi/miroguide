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

    def get_url(self):
        return util.make_url('languages/%d' % self.id)

    def link(self):
        return util.make_link(self.get_url(), str(self))

    def __str__(self):
        return self.name

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.name)
