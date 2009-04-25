# Copyright (c) 2009 Michael C. Urbanski
# See LICENSE for details.

import tables

from django.db import models
from sqlhelper.orm import Record
from channelguide.guide.tables import item

MOD_TYPE_ADDED = 1
MOD_TYPE_REMOVED = (-1)

class ChannelItemDelta (Record):
    table = tables.channel_item_delta
    
    def __init__(self, item=None, channel_id = None, item_id=None, mod_type=None):
        if item is not None:
            self.item_id = item.id
            self.channel_id = item.channel.id
            
        if channel_id is not None:
            self.channel_id = channel_id

        if item_id is not None:
            self.item_id = item_id

        if mod_type is not None:
            self.mod_type = mod_type

class ChannelSubscription (Record):
    table = tables.channel_subscription

    def __init__(self, user=None, channel=None, user_id=None, channel_id=None):
        if user is not None:
            self.user_id = user.id
        elif user_id is not None:
            self.user_id = user_id

        if channel is not None:
            self.channel_id = channel.id
        elif channel_id is not None:
            self.channel_id = channel_id

class ChannelSubscriptionDelta (Record):
    table = tables.channel_subscription_delta

    def __init__(self, user=None, channel=None, user_id=None, channel_id=None, mod_type=None):
        if user is not None:
            self.user_id = user.id
        elif user_id is not None:
            self.user_id = user_id

        if channel is not None:
            self.channel_id = channel.id
        elif channel_id is not None:
            self.channel_id = channel_id

        if mod_type is not None:
            self.mod_type = mod_type

class DownloadRequest (Record):
    table = tables.download_request

    def __init__(self, user=None, item=None, user_id=None, item_id=None):
        if user is not None:
            self.user_id = user.id
        elif user_id is not None:
            self.user_id = user_id

        if item is not None:
            self.item_id = item.id
        elif item_id is not None:
            self.item_id = item_id
            
class DownloadRequestDelta (Record):
    table = tables.download_request_delta

    def __init__(self, user=None, item=None, user_id=None, item_id=None, mod_type=None):
        if user is not None:
            self.user_id = user.id
        elif user_id is not None:
            self.user_id = user_id

        if item is not None:
            self.item_id = item.id
        elif item_id is not None:
            self.item_id = item_id

        if mod_type is not None:
            self.mod_type = mod_type
