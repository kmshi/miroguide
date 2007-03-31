import random

from sqlalchemy import func, select, Select, class_mapper
from sqlalchemy.exceptions import InvalidRequestError
from sqlalchemy.sql import (_BinaryClause, _CompoundClause, text, literal,
        _CompareMixin)

def select_random(select_result, count=1):
    all_results = select_result.list()
    if count >= len(all_results):
        return all_results
    else:
        return random.sample(select_result.list(), count)
    row_count = select_result.count()
    # The following is a completely blind opmitization without any numbers
    # behind it, but my intuition tells me that method 1 is faster when the
    # number of rows in the table is large compared to the count argument.
    # Method two is faster when the number of rows we're looking for is close
    # to the size of the table, and also works if count is greater than the
    # table size.
    if row_count == 0:
        return []
    elif float(count) / row_count < 0.5:
        indexes = random.sample(xrange(row_count), count)
        return [select_result[i] for i in indexes]
    else:
        return select_result.order_by(func.rand())[:count]

def count_distinct(*args, **kwargs):
    "Easy way to do a COUNT(DISTICT(column)) in SQLAlchemy."""
    return func.count(func.distinct(*args, **kwargs))

def correlate(table, parent_table):
    clauses = []
    for column in table.columns:
        for fk in column.foreign_keys:
            other = parent_table.corresponding_column(fk.column, False)
            if other is not None and other.primary_key:
                clauses.append(column == other)
                break
    if len(clauses) == 0:
        msg = "Can't correlate %s to %s" % (table, parent_table)
        raise InvalidRequestError(msg)
    elif len(clauses) > 1:
        msg = "Can't correlate %s to %s (too many foreign keys)" % (table,
            parent_table)
        raise InvalidRequestError(msg)
    else:
        return clauses[0]

class ScalarSubuerySelect(Select):
    """Scalar subquery that performs an aggregate subquery.

    The main point of this class is that it automatically correlates itself to
    the parent query.  For example:

    foo = Table('foo', metadata,
        Column('id', Integer, nullable=False, primary_key=True))
    bar = Table('bar', metadata,
        Column('id', Integer, nullable=False, primary_key=True),
        Column('foo_id', Integer, ForeignKey('foo.id'), nullable=False))

    >>> print select([foo, ScalarSubuerySelect(func.count('*'), bar)])

    SELECT foo.id,
           (SELECT count(bar.id) FROM bar WHERE bar.foo_id=foo.id)
    FROM foo

    (Note that ScalarSubuerySelect added "bar.foo_id=foo.id")
    """

    def __init__(self, aggregate_function, table):
        self.table = table
        super(ScalarSubuerySelect, self).__init__([aggregate_function],
                from_obj=[table], scalar=True)

    def correlate(self, from_obj):
        super(ScalarSubuerySelect, self).correlate(from_obj)
        self.append_whereclause(correlate(self.table, from_obj))

def aggregate_subquery(label, aggregate_function, table, *filters):
    s = ScalarSubuerySelect(aggregate_function, table)
    for clause in filters:
        s.append_whereclause(clause)
    return s.label(label)

def count_subquery(label, table, *filters):
    return aggregate_subquery(label, func.count('*'), table, *filters)

class MatchClause(_BinaryClause, _CompareMixin):
    def __init__(self, columns, query, boolean=False):
        self.boolean = boolean
        self.match = func.MATCH(*columns)
        query_clauses = [text('('), literal(query)]
        if self.boolean:
            query_clauses.append("IN BOOLEAN MODE")
        query_clauses.append(text(')'))
        self.query = _CompoundClause(None, *query_clauses)
        _BinaryClause.__init__(self, self.match, self.query, "AGAINST")

def match(columns, query, boolean=False):
    """MySQL match query."""
    return MatchClause(columns, query, boolean)
