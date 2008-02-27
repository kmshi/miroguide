# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from channelguide.guide import tables
from sqlhelper.orm import Record


class ChannelSearchData(Record):
    table = tables.channel_search_data

class ItemSearchData(Record):
    table = tables.item_search_data
