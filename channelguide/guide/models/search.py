from channelguide import util
from channelguide.guide import tables
from sqlhelper.orm import Record
from sqlhelper.orm.columns import AbstractColumn
from sqlhelper.sql.clause import Where

class ScoreColumn(AbstractColumn):
    def __init__(self, table, terms):
        AbstractColumn.__init__(self, 'score')
        self.query = ' '.join(terms)
        self.table = table

    def add_to_select(self, select):
        match_expr = '(MATCH(#table#.important_text) AGAINST (%s)) * 5 + \
(MATCH(#table#.important_text, #table#.text) AGAINST (%s)) AS #table#_score'
        match_expr = match_expr.replace('#table#', self.table.name)
        select.add_column(match_expr, self.query, self.query)

    def fullname(self):
        return '%s_score' % self.table.name

class SearchWhere(Where):
    def __init__(self, table, terms):
        query = ' '.join(terms)
        self.text = 'MATCH(#table#.important_text, #table#.text) AGAINST (%s \
IN BOOLEAN MODE)'
        self.text = self.text.replace('#table#', table.name)
        self.args = [query]

class SearchData(Record):
    @classmethod
    def search(cls, terms):
        terms = util.ensure_list(terms)
        query = cls.query()
        query.add_column(ScoreColumn(cls.table, terms))
        query.filter(SearchWhere(cls.table, terms))
        return query

class ChannelSearchData(SearchData):
    table = tables.channel_search_data

class ItemSearchData(SearchData):
    table = tables.item_search_data
