from channelguide.db import DBObject, dbutil
from sqlalchemy import select, text, desc, join, func

class FullTextSearchable:
    """Mixin class that helps with full text search capabilities."""

    def refresh_search_data(self):
        search_data = self.session().get(self.search_data_class, self.id)
        if search_data is None:
            search_data = self.search_data_class(self.id)
        self.fill_search_data(search_data)
        dbutil.save_if_new(self.session(), search_data)

    def get_search_data(self):
        values = [getattr(self, attr) for attr in self.search_attributes]
        return ' '.join(values)

    def get_search_data_important(self):
        attr_list = self.search_attributes_important
        values = [getattr(self, attr) for attr in attr_list]
        return ' '.join(values)

    def fill_search_data(self, search_data):
        search_data.text = self.get_search_data()
        search_data.important_text = self.get_search_data_important()

    @staticmethod
    def _search_where_clause():
        return text("MATCH(important_text, text) AGAINST "
                    "(:boolean_query IN BOOLEAN MODE)")

    @classmethod
    def _build_search_select(cls, columns, limit=None):
        score = text("(MATCH(important_text) AGAINST (:search_query)) * 5"
                "+ (MATCH(important_text, text) AGAINST (:search_query)) "
                "AS score")
        s = select(columns + [score], cls._search_where_clause(),
                limit=limit)
        s.order_by(desc('score'))
        return s

    @staticmethod
    def _search_execute_params(terms):
        return {
            'search_query': ' '.join(terms),
            'boolean_query': ' '.join(['+%s*' % t for t in terms]),
        }

    @classmethod
    def _execute_search(cls, connection, select, terms):
        return connection.execute(select, **cls._search_execute_params(terms))

    @classmethod
    def count_search_results(cls, connection, terms):
        table = cls.search_data_class.mapper().local_table
        s = select([func.count('*')], cls._search_where_clause(),
                from_obj=[table])
        results = connection.execute(s, **cls._search_execute_params(terms))
        return list(results)[0][0]

    @classmethod
    def search(cls, db_session, terms, limit=None):
        table = cls.mapper().local_table
        sort_table = cls.search_data_class.mapper().local_table

        select = cls._build_search_select([table], limit)
        select.append_from(join(sort_table, table))

        q = db_session.query(cls)
        connection = db_session.connection(cls.mapper())
        return q.instances(cls._execute_search(connection, select, terms))

    @classmethod
    def id_search(cls, connection, terms, limit=None):
        id = cls.search_data_class.mapper().primary_key
        select = cls._build_search_select(list(id), limit)
        results = cls._execute_search(connection, select, terms)
        if len(id) == 1:
            return [row[0] for row in results]
        else:
            # this should cover multi-column primary keys
            return [row[:len(id)] for row in results]

class ChannelSearchData(DBObject):
    def __init__(self, channel_id):
        self.channel_id = channel_id

class ItemSearchData(DBObject):
    def __init__(self, item_id):
        self.item_id = item_id
