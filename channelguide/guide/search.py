"""search channels."""
from channelguide import util
from channelguide.guide import tables
from channelguide.guide.models import Channel, ItemSearchData
from sqlhelper import sql

class Match(sql.Expression):
    def __init__(self, query, *columns):
        joined = sql.join(columns, ', ')
        self.text = 'MATCH(%s) AGAINST(%%s)' % joined.text
        self.args = list(joined.args)
        self.args.append(query)

class BooleanMatch(sql.Expression):
    def __init__(self, query, *columns):
        joined = sql.join(columns, ', ')
        self.text = 'MATCH(%s) AGAINST(%%s IN BOOLEAN MODE)' % joined.text
        self.args = list(joined.args)
        self.args.append(query)

def search_score(table, terms):
    query = ' '.join(terms)
    important = Match(query, table.c.important_text)
    normal = Match(query, table.c.important_text, table.c.text)
    return important * 50 + normal

def search_where(table, terms):
    query = ' '.join(u'+%s*' % t for t in terms)
    return BooleanMatch(query, table.c.important_text, table.c.text)

class ChannelItemSearchSelect(sql.CompoundExpression):
    def __init__(self, terms):
        text = """\
SELECT channel_id, MAX(%s) AS score
FROM cg_channel_item
JOIN cg_item_search_data ON id=item_id
WHERE %s
GROUP BY channel_id"""
        sql.CompoundExpression.__init__(self, text, 
        search_score(tables.item_search_data, terms),
        search_where(tables.item_search_data, terms))

def contains_hd(terms):
    return 'hd' in [term.lower() for term in terms]

def search_channels(terms):
    terms = util.ensure_list(terms)
#    terms = [t.encode('utf-8') for t in terms]
    query = Channel.query().join('search_data')
    search_data_table = query.joins['search_data'].table
    if contains_hd(terms):
        query.where(hi_def=1)
        terms = [t for t in terms if t.lower() != 'hd']
    query.where(search_where(search_data_table, terms))
    query.order_by(search_score(search_data_table, terms), desc=True)
    return query

def search_items(terms):
    terms = util.ensure_list(terms)
#    terms = [t.encode('utf-8') for t in terms]
    item_search_select = ChannelItemSearchSelect(terms)
    query = Channel.query()
    query.add_raw_join(item_search_select.label('search_data'),
            'cg_channel.id=search_data.channel_id')
    query.order_by('search_data.score', desc=True)
    return query
