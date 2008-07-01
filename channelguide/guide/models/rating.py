# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from channelguide.guide import tables
from sqlhelper.orm import Record

class Rating(Record):
    table = tables.channel_rating

class GeneratedRatings(Record):
    table = tables.generated_ratings
