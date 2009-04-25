# Copyright (c) 2009 Michael C. Urbanski
# See LICENSE for details.

from datetime import datetime
from django.utils.translation import gettext as _

from sqlhelper.orm import Table, columns
from channelguide.guide.tables import channel, item, user

def name_for_mod_type (mod_type):
    if mod_type == 1:
        return _('Added')
    else:
        return _('Removed')

channel_item_delta = Table (
  'aether_channel_item_delta',
  columns.Int ('id', primary_key=True, auto_increment=True),
  columns.Int ('channel_id', fk=channel.c.id),
  columns.Int ('item_id', fk=item.c.id),
  columns.Int ('mod_type', 1, default=1),
  columns.DateTime ('created_at', default=datetime.utcnow)
)

channel_subscription = Table (
  'aether_channel_subscription',
  columns.Int ('user_id', fk=user.c.id, primary_key=True),
  columns.Int ('channel_id', fk=channel.c.id, primary_key=True),
  columns.DateTime ('created_at', default=datetime.utcnow)
)

channel_subscription_delta = Table (
  'aether_channel_subscription_delta',
  columns.Int ('id', primary_key=True, auto_increment=True),
  columns.Int ('user_id', fk=user.c.id),
  columns.Int ('channel_id', fk=channel.c.id),
  columns.Int ('mod_type', 1, default=1),
  columns.DateTime ('created_at', default=datetime.utcnow)
)

download_request = Table (
  'aether_download_request',
  columns.Int ('user_id', fk=user.c.id, primary_key=True),
  columns.Int ('item_id', fk=item.c.id, primary_key=True),
  columns.DateTime ('created_at', default=datetime.utcnow),
  columns.DateTime ('imparted_on', default=None)
)

download_request_delta = Table (
  'aether_download_request_delta',
  columns.Int ('id', primary_key=True, auto_increment=True),
  columns.Int ('user_id', fk=user.c.id),
  columns.Int ('item_id', fk=item.c.id),
  columns.Int ('mod_type', 1, default=1),
  columns.DateTime ('created_at', default=datetime.utcnow)
)

channel_item_delta.many_to_one (
  'channel_item', item, backref='item_deltas',
  join_column=channel_item_delta.c.item_id
)

channel_subscription.many_to_one (
  'channel', channel, backref='subscriptions',
  join_column=channel_subscription.c.channel_id
)

channel_subscription.many_to_one (
  'user', user, backref='subscriptions',
  join_column=channel_subscription.c.user_id
)

channel_subscription_delta.many_to_one (
  'subscription_item', channel, backref='subscription_deltas',
  join_column=channel_subscription_delta.c.channel_id
)

download_request.many_to_one (
  'user', user, backref='download_requests',
  join_column=download_request.c.user_id
)

download_request.many_to_one (
  'item', item, backref='download_requests',
  join_column=download_request.c.item_id
)

download_request_delta.many_to_one (
  'user', user, join_column=download_request_delta.c.user_id
)

download_request_delta.many_to_one (
  'item', item, join_column=download_request_delta.c.item_id
)
