"""query.py

Contains the Query and Join classes, a higher level, object based version of
SQL selects.  Query objects handle selecting rows from the database and
converting them to Record objects.  Join objects do the same for joined
tables.
"""

from itertools import izip, count

from sqlhelper import sql, util
from sqlhelper.exceptions import NotFoundError, TooManyResultsError
from sqlhelper.sql import clause
import columns
import relations

def null_primary_key(primary_key_values):
    for value in primary_key_values:
        if value is not None:
            return False
    return True

class Selector(object):
    """Base class for Query, Join and ResultJoiner."""
    def __init__(self, table):
        self.table = table
        self.c = self.columns = columns.ColumnStore()
        self.joins = {}

    def get_column(self, name_or_column):
        if isinstance(name_or_column, columns.ColumnBase):
            return name_or_column
        else:
            return getattr(self.columns, name_or_column)

    def path_to_join(self, join_name):
        path = []
        selector = self
        for component in join_name.split('.'):
            selector = selector.joins[component]
            path.append(selector)
        return path

    def join(self, *relation_names):
        for name in relation_names:
            if '.' not in name:
                alias = self.make_join_alias(name)
                join = Join(self.table.relations[name], alias)
                self.joins[name] = join
            else:
                name, rest = name.split('.', 1)
                self.joins[name].join(rest)
        return self

    def make_join_alias(self, name):
        return 'r_%s' % name

    def join_iterator(self):
        for join in self.joins.values():
            yield self, join
            for parent, subjoin in join.join_iterator():
                yield parent, subjoin

    def add_joins(self, select):
        for parent, join in self.join_iterator():
            join.columns.add_to_select(select)
            join.relation.add_joins(select, parent.table, join.table)

    def make_record(self, rowid, data):
        """Create a record from the data that was consumed."""
        raise NotImplementedError()

class TableSelector(Selector):
    """Selector that selects an entire table."""

    def __init__(self, table):
        Selector.__init__(self, table)
        self.columns.add_columns(table.regular_columns)

    def add_column(self, column):
        self.columns.add_column(column)
        return self

    def add_columns(self, *columns):
        self.columns.add_columns(columns)
        return self

    def load(self, *column_names):
        for name in column_names:
            self.add_column(getattr(self.table.c, name))
        return self

    def make_record(self, rowid, data):
        record_class = self.table.record_class
        record = record_class.__new__(record_class)
        record.rowid = rowid
        for column, obj in izip(self.columns, data):
            setattr(record, column.name, column.convert_from_db(obj))
        for join in self.joins.values():
            join.relation.init_record(record)
        record.on_restore()
        return record

class Query(TableSelector):
    """Handles selecting Records from a table"""
    def __init__(self, table):
        TableSelector.__init__(self, table)
        self.wheres = []
        self.havings = []
        self.filter_joins = []
        self._order_by = []
        self.desc = False
        self._limit = None
        self._offset = None

    def filter(self, *filters, **attribute_filters):
        for filter in filters:
            self._add_filter(filter)
        for name, value in attribute_filters.items():
            column = self.get_column(name)
            self._add_filter(column==value)
        return self

    def filter_join(self, join_name, *filters, **attribute_filters):
        join_path = self.path_to_join(join_name)
        for join in join_path:
            if type(join.relation) not in (relations.ManyToOne, 
                    relations.OneToOne):
                msg = 'can only filter many-to-one or one-to-one relations'
                raise TypeError(msg)
        self.extend_filter_joins(join_path)
        join = join_path[-1]
        for filter in filters:
            for arg in filter.args:
                filter.alias(join.table)
                self._add_filter(filter)
        for name, value in attribute_filters.items():
            column = join.get_column(name)
            self._add_filter(column==value)

    def extend_filter_joins(self, join_path):
        parent = self
        for join in join_path:
            self.filter_joins.append((parent, join))
            parent = join

    def _add_filter(self, filter):
        if isinstance(filter, clause.Where):
            self.wheres.append(filter)
        elif isinstance(filter, clause.Having):
            self.havings.append(filter)
        else:
            raise TypeError("Wrong type for filter: %s" % type(filter))

    def order_by(self, order_by, desc=False):
        if order_by is None:
            self._order_by = []
            return self
        try:
            order_by = self.get_column(order_by).fullname()
        except AttributeError:
            pass
        self._order_by.append(clause.OrderBy(order_by, desc))
        return self

    def limit(self, count):
        self._limit = count
        return self

    def offset(self, count):
        self._offset = count
        return self

    def make_select(self):
        select = sql.Select()
        if not self._need_subquery():
            self.columns.add_to_select(select)
            select.add_from(self.table)
            self.add_filters_to_select(select)
            select.limit = self._limit
            select.offset = self._offset
        else:
            subquery = self._make_subquery()
            select.froms.append(subquery.as_subquery(self.table.name))
            select.add_column('%s.*' % self.table.name)
        select.order_by = self._order_by
        self.add_joins(select)
        return select

    def add_filters_to_select(self, select):
        select.wheres.extend(self.wheres)
        select.havings.extend(self.havings)

    def add_filter_joins_to_select(self, select):
        already_joined = set()
        for parent, join in self.filter_joins:
            if join not in already_joined:
                join.relation.add_joins(select, parent.table, join.table)
            already_joined.add(join)

    def _need_subquery(self):
        """If we are selecting a one-to-many or many-to-many relation for this
        select, then we will get back more rows than records that are selected
        and using LIMIT or OFFSET in a naive won't work.

        The trick is to use a subquery to figure out which records to select
        and label that subquery with the same name as our table.  For example:

        SELECT foo.id, foo.name
        FROM (SELECT foo.id, foo.name FROM foo LIMIT 5) AS foo
        LEFT JOIN bar ON bar.foo_id = foo.id
        """
        if not self._limit and not self._offset:
            return False
        for parent, join in self.join_iterator():
            klass = type(join.relation)
            if klass in (relations.OneToMany, relations.ManyToMany):
                return True
        return False

    def _make_subquery(self):
        subquery = sql.Select()
        self.columns.add_to_select(subquery)
        subquery.add_from(self.table)
        self.add_filter_joins_to_select(subquery)
        self.add_filters_to_select(subquery)
        subquery.order_by = self._order_by
        subquery.limit = self._limit
        subquery.offset = self._offset
        return subquery

    def execute(self, cursor, select=None):
        if select is None:
            select = self.make_select()
        result_handler = ResultHandler(self)
        for row in select.execute(cursor):
            row_iter = iter(row)
            result_handler.handle_data(row_iter)
        return result_handler.make_results()

    def get(self, cursor, id=None):
        if id is not None:
            id_values = util.ensure_list(id)
            for col, value in zip(self.table.primary_keys, id_values):
                self.filter(col==value)
        results = self.execute(cursor)
        if len(results) == 1:
            return results[0]
        elif len(results) == 0:
            raise NotFoundError("Record not found")
        else:
            raise TooManyResultsError("Too many records returned")

    def count(self, cursor):
        select = self.table.select_count()
        self.add_filter_joins_to_select(select)
        self.add_filters_to_select(select)
        return select.execute(cursor)[0][0]

    def __str__(self):
        return str(self.make_select())

class Join(TableSelector):
    def __init__(self, relation, alias_name):
        self.relation = relation
        aliased = relation.related_table.alias(alias_name)
        TableSelector.__init__(self, aliased)

    def make_join_alias(self, name):
        return 'r_%s_%s' % (self.relation.name, name)

class ResultHandler(object):
    """Handles results as they come back from the database."""
    
    def __init__(self, selector):
        self.selector = selector
        self.record_map = {}
        self.records = []
        self.children = [ResultHandler(join) for join in
                selector.joins.values()]
        self.primary_key_indicies = []
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
            return None # Left join resulted in a NULL result
        if pk in self.record_map:
            record = self.record_map[pk]
        else:
            record = self.selector.make_record(pk, data)
            self.records.append(record)
            self.record_map[pk] = record
        for child_handler in self.children:
            relation = child_handler.handle_data(row_iter)
            if relation is not None:
                child_handler.selector.relation.do_join(record, relation)
        return record

    def add_records(self, records):
        for record in records:
            self.records.append(record)
            self.record_map[record.primary_key_values()] = record

    def make_results(self):
        result_set = ResultSet(self.selector.table, self.records)
        self.fill_in_results(result_set)
        return result_set

    def fill_in_results(self, result_set):
        for child_handler in self.children:
            name = child_handler.selector.relation.name
            result_set.joins[name] = child_handler.make_results()

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

class ResultJoiner(Selector):
    """Selector that joins a ResultSet to its relations."""

    def __init__(self, result_set):
        Selector.__init__(self, result_set.table)
        self.result_set = result_set
        self.columns.add_columns(self.table.primary_keys)

    def make_select(self):
        select = sql.Select()
        select.add_from(self.table)
        self.columns.add_to_select(select)
        self.add_joins(select)
        if len(self.result_set.table.primary_keys) == 1:
            pk = self.result_set.table.primary_keys[0]
            where = pk.in_([r.rowid[0] for r in self.result_set])
            select.wheres.append(where)
        else:
            wheres = [r.rowid_where() for r in self.result_set]
            select.wheres.append(clause.Where.or_together(wheres))
        return select

    def no_joins(self):
        return len(self.joins) == 0

    def execute(self, cursor):
        if self.no_joins():
            return
        result_handler = ResultHandler(self)
        result_handler.add_records(self.result_set)
        for record in result_handler.records:
            for join in self.joins.values():
                join.relation.init_record(record)
        for row in self.make_select().execute(cursor):
            row_iter = iter(row)
            result_handler.handle_data(row_iter)
        result_handler.fill_in_results(self.result_set)

    def __str__(self):
        return str(self.make_select())
