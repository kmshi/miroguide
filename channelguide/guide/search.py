"""search channels."""
from channelguide import util
from channelguide.guide.models import Channel, ItemSearchData
from sqlhelper import sql
from sqlhelper.sql import clause

class SearchScore(clause.Clause):
    def __init__(self, table, terms):
        query = ' '.join(terms)
        self.text = ('(MATCH(#table#.important_text) AGAINST (%s)) * 50 + '
                '(MATCH(#table#.important_text, #table#.text) AGAINST (%s))')
        self.text = self.text.replace('#table#', str(table))
        self.args = [query, query]

class SearchWhere(clause.Where):
    def __init__(self, table, terms):
        query = ' '.join(terms)
        self.text = ('MATCH(#table#.important_text, #table#.text) '
                'AGAINST (%s IN BOOLEAN MODE)')
        self.text = self.text.replace('#table#', str(table))
        self.args = [query]

class ChannelItemSearchSelect(sql.Select):
    def __init__(self, terms):
        self.score = SearchScore('cg_item_search_data', terms)
        self.where = SearchWhere('cg_item_search_data', terms)

    def compile(self):
        text = """\
SELECT channel_id, MAX(%s) AS score
FROM cg_channel_item
JOIN cg_item_search_data ON id=item_id
WHERE %s
GROUP BY channel_id""" % (self.score.text, self.where.text)
        return text, (self.score.args + self.where.args)

def search_channels(terms):
    terms = util.ensure_list(terms)
    query = Channel.query().join('search_data')
    query.filter(state=Channel.APPROVED)
    search_data_table = query.joins['search_data'].table.name
    query.filter(SearchWhere(search_data_table, terms))
    query.order_by(SearchScore(search_data_table, terms), desc=True)
    return query

def search_items(terms):
    terms = util.ensure_list(terms)
    item_search_select = ChannelItemSearchSelect(terms)

    query = Channel.query()
    query.filter(state=Channel.APPROVED)
    query.add_raw_join(item_search_select.as_subquery('search_data'),
            'cg_channel.id=search_data.channel_id')
    query.order_by('search_data.score', desc=True)
    return query
