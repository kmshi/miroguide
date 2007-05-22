import logging
from sqlhelper.sql import clause

class ColumnStore(object):
    """Stores a bunch of columns.  Columns can be accessed as attributes, or
    by iterating through the ColumnStore object.
    """
    def __init__(self, columns=None):
        self.columns = []
        if columns is not None:
            self.extend(columns)

    def add(self, column):
        self.columns.append(column)
        setattr(self, column.name, column)

    def extend(self, columns):
        for column in columns:
            self.add(column)

    def get(self, name):
        return getattr(self, name)

    def add_to_select(self, select):
        for column in self.columns:
            column.add_to_select(select)

    def __iter__(self):
        return iter(self.columns)
    def __len__(self):
        return len(self.columns)

class Column(object):
    def __init__(self, name, primary_key=False, auto_increment=False, fk=None,
            optional=False, default=None, onupdate=None): 
        """Construct a column.  
        
        Arguments:

        name -- name of the column
        primary_key -- is the column is one of the primary keys for its table?
        auto_increment -- does this column an auto-incremented primary key?
        fk -- specifies that this column is a foreign key to that references
            another column.
        default -- default value for the column, this can be either a literal
           value, or a callable.
        onupdate -- callable that updates this column on every update
        """
        if auto_increment and not primary_key:
            raise ValueError("auto_increment can only be set for primary keys")
        self.name = name
        self.primary_key = primary_key
        self.auto_increment = auto_increment
        self.table = None
        self.ref = fk
        self.optional = optional
        self.default = default
        self.onupdate = onupdate

    def add_to_select(self, select):
        select.add_column(self.fullname())

    def make_filter(self, string, args):
        return clause.Where(string, args)

    def convert_from_db(self, data):
        """Convert data coming from MySQL."""
        return data

    def convert_for_db(self, data):
        """Convert data before it gets sent to MySQL."""
        return data

    def __str__(self):
        return self.fullname()

    def make_clause_string(self):
        return self.fullname()

    def fullname(self):
        if self.table is not None:
            return '%s.%s' % (self.table.name, self.name)
        else:
            return self.name

    def count_distinct(self):
        return clause.Column("COUNT(DISTINCT(%s))" % self.fullname())

    def _sql_operator(self, other, operator):
        if isinstance(other, Column):
            string = '%s %s %s' % (self.fullname(), operator, other.fullname())
            args = []
        elif isinstance(other, clause.Clause):
            string = '%s %s %s' % (self.fullname(), operator, other.text)
            args = other.args
        else:
            string = '%s %s %%s' % (self.fullname(), operator)
            args = [other]
        return self.make_filter(string, args)

    def __eq__(self, other):
        if other is not None:
            return self._sql_operator(other, '=')
        else:
            return self._sql_operator(other, 'IS')
    def __ne__(self, other):
        if other is not None:
            return self._sql_operator(other, '!=')
        else:
            return self._sql_operator(other, 'IS NOT')
    def __gt__(self, other):
        return self._sql_operator(other, '>')
    def __lt__(self, other):
        return self._sql_operator(other, '<')
    def __ge__(self, other):
        return self._sql_operator(other, '>=')
    def __le__(self, other):
        return self._sql_operator(other, '<=')

    def like(self, other):
        return self._sql_operator(other, 'LIKE')

    def in_(self, possible_values):
        percent_s = ['%s' for values in possible_values]
        string = "%s IN (%s)" % (self.fullname(), ', '.join(percent_s))
        return self.make_filter(string, possible_values)

    def validate(self, value):
        if not self.do_validate(value):
            self.on_validate_error(value)

    def do_validate(self, value):
        """Can be overridden by subclasses to validate a value to be
        stored.
        """
        return True

    def on_validate_error(self, value):
        raise ValueError("%s is not a valid value")

class Int(Column):
    pass

class String(Column):
    def __init__(self, name, length=None, *args, **kwargs):
        Column.__init__(self, name, *args, **kwargs)
        self.length = length

    def convert_for_db(self, data):
        if (self.length is not None and data is not None and 
                len(data) > self.length):
            logging.warn("Truncating data %r for column %s", data,
                    self.fullname())
            data = data[:self.length]
        return data

class DateTime(Column):
    pass

class Boolean(Column):
    def convert_from_db(self, data):
        """Convert data coming from MySQL."""
        return bool(data)

class AbstractColumn(Column):
    """Column that doesn't correspond to a column in the database.  This is
    used for things like subqueries, MySQL MATCH columns, etc.
    """
    def __init__(self, name, *args, **kwargs):
        if 'optional' not in kwargs:
            kwargs['optional'] = True
        super(AbstractColumn, self).__init__(name, *args, **kwargs)

    def fullname(self):
        if self.table is not None:
            return "%s_%s" % (self.table.name, self.name)
        else:
            return self.name

    def add_to_select(self, select):
        select.add_column(self.column_expression())

class Subquery(AbstractColumn):
    """Column that represents a SQL scalar subselect.

    Its argument should be a the SELECT string, but with the table replaced
    with "#table#".  e.g.

    Subquery('bar_count', 
             'SELECT COUNT(*) from bar where bar.foo_id=#table#.id')

    Replacing the table name with '#table#' allows handling table aliases
    correctly.
    """

    def __init__(self, name, sql, *args, **kwargs):
        super(Subquery, self).__init__(name, *args, **kwargs)
        self.sql = sql

    def column_expression(self):
        real_sql = self.sql.replace('#table#', self.table.name)
        return '(%s) AS %s' % (real_sql, self.fullname())

    def make_filter(self, string, args):
        return clause.Having(string, args)

    def __str__(self):
        return self.column_expression()

class Expression(AbstractColumn):
    def __init__(self, name, clause, *args, **kwargs):
        super(Expression, self).__init__(name, *args, **kwargs)
        self.clause = clause

    def column_expression(self):
        text = '(%s) AS %s' % (self.clause.text, self.fullname())
        return clause.Column(text, self.clause.args)
