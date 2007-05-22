"""Search channels."""
from channelguide.guide.models import (Channel, ChannelSearchData,
        ItemSearchData)
from sqlhelper.sql import clause

def channel_search_query(terms):
    query = ChannelSearchData.search(terms)
    query.join('channel')
    query.joins['channel'].filter(state=Channel.APPROVED)
    return query

def search_channels(connection, terms, offset=None, limit=None):
    query = channel_search_query(terms)
    if offset is not None:
        query.offset(offset)
    if limit is not None:
        query.limit(limit)
    query.order_by(query.c.score, desc=True)
    return query.execute(connection).joins['channel']

def count_channel_matches(connection, terms):
    return channel_search_query(terms).count(connection)

def item_search_query(terms):
    query = ItemSearchData.search(terms)
    query.join('item', 'item.channel')
    query.joins['item.channel'].filter(state=Channel.APPROVED)
    return query

def search_items(connection, terms, offset=None, limit=None):
    query = item_search_query(terms)
    if offset is not None:
        query.offset(offset)
    if limit is not None:
        query.limit(limit)
    query.order_by(query.c.score, desc=True)
    # This is a MySQL specific GROUP BY extension.  We only group by the
    # channel id, because we know that will generate unique values for all the
    # channel columns.  The item columns we don't care about.  FULL text
    # indexes are MySQL specific anyways, so I don't feel bad doing this...
    select = query.make_select()
    select.add_group_by(query.joins['item.channel'].c.id)
    return query.execute(connection, select=select).joins['item.channel']

def count_item_matches(connection, terms):
    query = item_search_query(terms)
    select = query.make_select()
    select.columns = [query.joins['item.channel'].c.id.count_distinct()]
    return select.execute_scalar(connection)
