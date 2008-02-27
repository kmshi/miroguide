# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from channelguide import util
from channelguide.guide import tables
from sqlhelper.orm import Record
from sqlhelper.orm.columns import Subquery
class Rating(Record):
    table = tables.channel_rating

class GeneratedRatings(Record):
    table = tables.generated_ratings
