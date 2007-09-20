"""query.py

Contains the Query and Join classes.  Queries and Joins perform object-based
SQL selects.  Query objects handle selecting rows from the database and
converting them to Record objects.  Join objects do the same for joined
tables.

Query objects are dumb.  For example, if you call limit() on a query, it just
sets the LIMIT part of the SELECT statement.  If the query gets joined to a
one-to-many relationship, you may get less records back then the limit amount.
"""

from itertools import izip, count

from sqlhelper import sql, util
from sqlhelper.exceptions import NotFoundError, TooManyResultsError
from sqlhelper.sql import expression
import columns
import relations
import time, pickle

USE_CACHE=True

def null_primary_key(primary_key_values):
    for value in primary_key_values:
        if value is not None:
            return False
    return True

class Selector(object):
    """Base class for Query, Join and ResultJoiner."""
    def __init__(self, table):
        super(Selector, self).__init__()
        self.table = table
        self.c = self.columns = columns.ColumnStore()
        self.join_list = []

    def get_column(self, name_or_column):
        if isinstance(name_or_column, columns.Column):
            return name_or_column
        else:
            return self.columns.get(name_or_column)

    def join_iterator(self):
        for join in self.join_list:
            yield self, join
            for parent, subjoin in join.join_iterator():
                yield parent, subjoin

    def make_record(self, rowid, data):
        """Create a record from the data that was consumed."""
        raise NotImplementedError()

class TableSelector(Selector):
    """Selector that selects an entire table."""

    def __init__(self, table):
        super(TableSelector, self).__init__(table)
        self.columns.extend(table.regular_columns)
        self.wheres = []
        self.havings = []

    def where(self, *expressions, **attribute_filters):
        """Add a where expression, or multiple where expressions to the query.
        If multiple where expressions are added to the query, they will all be
        ANDed together.

        There are 2 ways to pass in where expressions:
          - make Expression objects and pass them in as positional arguments
          - pass in keyword arguments in the form of <column-name>=<value>
        """
        self.wheres.extend(expressions)
        self.wheres.extend(self._make_filters(attribute_filters))
        return self

    def having(self, *expressions, **attribute_filters):
        """Add HAVING expressions.  This works exactly like where(), except
        the expressions will be added to the HAVING part of the query.
        """
        self.havings.extend(expressions)
        self.havings.extend(self._make_filters(attribute_filters))
        return self

    def _make_filters(self, attribute_filters):
        filters = []
        for name, value in attribute_filters.items():
            column = self.get_column(name)
            if value is not None:
                filters.append(column==value)
            else:
                filters.append(column.is_(None))
        return filters

    def add_filters_to_select(self, select):
        select.wheres.extend(self.wheres)
        select.havings.extend(self.havings)

    def add_column(self, column):
        self.columns.add(column)
        return self

    def add_columns(self, *columns):
        self.columns.extend(columns)
        return self

    def load(self, *column_names):
        for name in column_names:
            self.add_column(self.table.columns.get(name))
        return self

    def make_record(self, rowid, data):
        record_class = self.table.record_class
        record = record_class.__new__(record_class)
        record.rowid = rowid
        for column, obj in izip(self.columns, data):
            setattr(record, column.name, column.convert_from_db(obj))
        for join in self.join_list:
            join.relation.init_record(record)
        record.on_restore()
        return record

class Joiner(object):
    def __init__(self):
        super(Joiner, self).__init__()
        self.joins = {}
        self.raw_joins = []

    def join(self, *relation_names):
        for name in relation_names:
            if '.' not in name:
                selector = self
                relation_name = name
            else:
                join_name, relation_name = name.rsplit('.', 1)
                selector = self.joins[join_name]
            alias = 'r_%s' % name.replace('.', '_')
            join = Join(selector.table.relations[relation_name], alias)
            selector.join_list.append(join)
            self.joins[name] = join
        return self

    def start_select(self):
        select = sql.Select()
        self.columns.add_to_select(select)
        from_table = self.table
        for parent, join in self.join_iterator():
            join.columns.add_to_select(select)
            join.add_filters_to_select(select)
            from_table = join.relation.add_join(from_table, parent.table, 
                    join.table)
        for table, on, type in self.raw_joins:
            from_table = from_table.join(table, on, type)
        select.froms.append(from_table)
        return select

    def add_raw_join(self, table, on, type='INNER'):
        """Adds a join expression to the SELECT statement used in this query.
        Unlike join(), this doesn't add a relation to the Records outputted
        from execute(), it only adds a JOIN at the SQL level.  The reason to
        use this is to use the joined tables for filters and order_bys.
        """
        self.raw_joins.append((table, on, type))

class Query(TableSelector, Joiner):
    """Handles selecting Records from a table"""
    def __init__(self, table):
        super(Query, self).__init__(table)
        self._order_by = []
        self.desc = False
        self._limit = None
        self._offset = None
        self.cacheable = False
        self.cachable_time = 0

    def __getstate__(self):
        d = self.__dict__.copy()
        d['cacheable'] = None
        d['cacheable_time'] = 0
        return d

    def order_by(self, order_by, desc=False):
        """Change the row ordering for this query.  order_by can either be a
        Expression object, or the name of a column.  If order_by() can be
        called multiple times to order the rows by multiple columns.  For
        example:

        query.order_by('foo')
        query.order_by('bar', desc=True)

        results in:

        ORDER BY foo, bar DESC

        Pass in None to clear the list of order by columns.
        """

        if order_by is None:
            self._order_by = []
            return self
        if isinstance(order_by, str):
            try:
                order_by = self.get_column(order_by)
            except AttributeError:
                pass
        self._order_by.append(sql.OrderBy(order_by, desc))
        return self

    def limit(self, count):
        self._limit = count
        return self

    def offset(self, count):
        self._offset = count
        return self

    def make_select(self):
        select = self.start_select()
        self.add_filters_to_select(select)
        select.limit = self._limit
        select.offset = self._offset
        if self._order_by:
            select.order_by = self._order_by
        else:
            # by default order by the primary key(s)
            for column in self.table.primary_keys:
                select.order_by.append(sql.OrderBy(column))
        return select

    def execute(self, connection, select=None):
        if select is None:
            select = self.make_select()
        if USE_CACHE:
            key = 'SQL%i' % hash(select.compile())
            if self.cacheable:
                cached = self.cacheable.get(key)
                if cached:
                    return cached
            s = time.time()
        result_handler = ResultHandler(self)
        for row in select.execute(connection):
            row_iter = iter(row)
            result_handler.handle_data(row_iter)
        results = result_handler.make_results()
        if USE_CACHE:
            e = time.time()
            if e-s>0.25:
                file('/tmp/expensive.sql', 'a').write("""%sexecuting %s (%s)
%r
took too long: %f
    """ % (self.cacheable and '*' or ' ', self, key, pickle.dumps(self, 2), e-s))
            if self.cacheable:
                self.cacheable.set(key, list(results), time=self.cacheable_time)
        return results

    def get(self, connection, id=None):
        if id is not None:
            id_values = util.ensure_list(id)
            for col, value in zip(self.table.primary_keys, id_values):
                self.where(col==value)
        results = self.execute(connection)
        if len(results) == 1:
            return results[0]
        elif len(results) == 0:
            raise NotFoundError("Record not found")
        else:
            raise TooManyResultsError("Too many records returned")

    def count(self, connection):
        select = self.make_select()
        select.order_by = None
        select.columns = [sql.COUNT]
        return select.execute_scalar(connection)

    def __str__(self):
        return str(self.make_select())

class Join(TableSelector):
    def __init__(self, relation, alias_name):
        self.relation = relation
        aliased = relation.related_table.alias(alias_name)
        super(Join, self).__init__(aliased)

class ResultHandler(object):
    """Handles results as they come back from the database."""
    
    def __init__(self, selector):
        self.selector = selector
        self.record_map = {}
        self.records = []
        self.children = [ResultHandler(join) for join in selector.join_list]
        self.primary_key_indicies = []
        self.joins_done = set()
        for i, column in izip(count(), selector.columns):
            if column.primary_key:
                self.primary_key_indicies.append(i)

    def read_data(self, row_iter):
        return [row_iter.next() for i in xrange(len(self.selector.columns))]

    def primary_key_from_data(self, data):
        return tuple(data[i] for i in self.primary_key_indicies)

    def handle_data(self, row_iter):
        """Handles incoming data from the database.  

        row_iter is an iterable over the returned row.  It should start by
        pointing at the start of the data for this ResultHandler's record.
        After handle_data, it will point at the next record.
        """

        data = self.read_data(row_iter)
        pk = self.primary_key_from_data(data)
        if null_primary_key(pk):
            # Left join resulted in a NULL result
            record = None 
        elif pk in self.record_map:
            record = self.record_map[pk]
        else:
            record = self.selector.make_record(pk, data)
            self.records.append(record)
            self.record_map[pk] = record
        for child_handler in self.children:
            relation = child_handler.handle_data(row_iter)
            if (record is not None and relation is not None and 
                    (record, relation) not in self.joins_done):
                child_handler.selector.relation.do_join(record, relation)
                self.joins_done.add((record, relation))
        return record

    def add_records(self, records):
        for record in records:
            self.records.append(record)
            self.record_map[record.primary_key_values()] = record

    def make_results(self):
        result_set = ResultSet(self.selector.table, self.records)
        self.add_joined_results(result_set)
        return result_set

    def add_joined_results(self, result_set, path=None):
        if path is None:
            path = []
        for child in self.children:
            path.append(child.selector.relation.name)
            name = '.'.join(path)
            child_results = ResultSet(child.selector.table, child.records)
            result_set.joins[name] = child_results
            child.add_joined_results(result_set, path)
            path.pop()

class ResultSet(object):
    """The results of a Query."""

    def __init__(self, table, records):
        self.table = table
        self.records = records
        self.joins = {}

    def values_for_column(self, column):
        """Get the set of values for a column that are present in this record
        list.
        """
        return set([getattr(r, column.name) for r in self])

    def join(self, *relation_names):
        """Perform joins on returned records.

        This method does the equivilent of Query.join(), but it does it for
        records that have already been returned by the database.  This has the 
        advantage is that it can lead to less rows returned from the database,
        the disadvantage is that it takes multiple round-trips.

        The case to use this is when you are joining to multiple one-to-many,
        or many-to-many relations that each have many results at the other
        end.  For example, suppose you are selecting 15 channels, and each
        channel will be joined to 10 categories and 5 tags.  Using a single
        select will return 15 * 10 * 5 == 750 rows.  Using a select that joins
        the channels to tags, then joining the results to the categories
        results in (15 * 10) + (15 * 5) = 225 rows.
        """

        return ResultJoiner(self).join(*relation_names)

    # Emulate a list
    def __iter__(self):
        return iter(self.records)
    def __len__(self):
        return len(self.records)
    def __getitem__(self, idx):
        return self.records[idx]
    def __repr__(self):
        return '%s: %s' % (self.__class__.__name__, repr(self.records))

class ResultJoiner(Selector, Joiner):
    """Selector that joins a ResultSet to its relations."""

    def __init__(self, result_set):
        super(ResultJoiner, self).__init__(result_set.table)
        self.result_set = result_set
        self.columns.extend(self.table.primary_keys)

    def make_select(self):
        select = self.start_select()
        if len(self.result_set.table.primary_keys) == 1:
            pk = self.result_set.table.primary_keys[0]
            where = pk.in_([r.rowid[0] for r in self.result_set])
            select.wheres.append(where)
        else:
            wheres = [r.rowid_where() for r in self.result_set]
            select.wheres.append(sql.or_together(wheres))
        return select

    def no_joins(self):
        return len(self.joins) == 0

    def execute(self, connection):
        if self.no_joins():
            return
        result_handler = ResultHandler(self)
        result_handler.add_records(self.result_set)
        for record in result_handler.records:
            for join in self.join_list:
                join.relation.init_record(record)
        for row in self.make_select().execute(connection):
            row_iter = iter(row)
            result_handler.handle_data(row_iter)
        result_handler.add_joined_results(self.result_set)

    def __str__(self):
        return str(self.make_select())
