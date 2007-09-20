import logging
import datetime
from sqlhelper import sql 

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

class Column(sql.SimpleExpression):
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
        self.args = []

    def get_text(self):
        return self.fullname()
    text = property(get_text)

    def column_expression(self):
        """Return the Expression used to define the column (normally this just
        returns self, but in the case of a Subquery column it's not the same.
        """
        return self

    def add_to_select(self, select):
        select.columns.append(self.column_expression())

    def convert_from_db(self, data):
        """Convert data coming from MySQL."""
        return data

    def convert_for_db(self, data):
        """Convert data before it gets sent to MySQL."""
        return data

    def __str__(self):
        exp = self.column_expression()
        if exp.args:
            return "<%s: %s ARGS: %s>" % (self.__class__.__name__, exp.text, exp.args)
        else:
            return '<%s: %s>' % (self.__class__.__name__, exp.text)

    def fullname(self):
        if self.table is not None:
            return '%s.%s' % (self.table.name, self.name)
        else:
            return self.name

    def count_distinct(self):
        return sql.SimpleExpression("COUNT(DISTINCT(%s))" % self.fullname())

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
    """String columns store str and unicode objects.  By default unicode
    objects will be encoding with utf-8 encoding, but this can be changed 2
    ways:

    The system-wide encoding can be changed with the class attribute
    'encoding', (String.encoding = 'latin1')

    A specific column's encoding can be changed by setting an attribute on
    that object, (foo.columns.string_column.encoding = 'latin1')

    """
    encoding = 'utf8'

    def __init__(self, name, length=None, *args, **kwargs):
        Column.__init__(self, name, *args, **kwargs)
        self.length = length

    def convert_for_db(self, data):
        if isinstance(data, unicode):
            data = data.encode(self.encoding)
        if (self.length is not None and data is not None and 
                len(data) > self.length):
            logging.warn("Truncating data %r for column %s", data,
                    self.fullname())
            data = data[:self.length]
        return data

class DateTime(Column):
    def __getstate__(self):
        """
        datetime.now can't be pickled, so we replace it on pickling and
        replacing on unpickling.
        """
        d = self.__dict__.copy()
        if 'default' in d and self.default is datetime.datetime.now:
            d['default'] = -1
        if 'onupdate' in d and self.onupdate is datetime.datetime.now:
            d['onupdate'] = -1
        return d


    def __setstate__(self, state):
        self.__dict__ = state
        if self.default == -1:
            self.default = datetime.datetime.now
        if self.onupdate == -1:
            self.onupdate = datetime.datetime.now

class Boolean(Column):
    def convert_from_db(self, data):
        """Convert data coming from MySQL."""
        return bool(data)

class AbstractColumn(Column):
    """Column that doesn't correspond to a column in the database.  This is
    used for things like subqueries, expressions, etc.
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
        return sql.Expression('(%s) AS %s' % (real_sql, self.fullname()))

class Expression(AbstractColumn):
    def __init__(self, name, expression, *args, **kwargs):
        super(Expression, self).__init__(name, *args, **kwargs)
        self.expression = expression

    def column_expression(self):
        return self.expression.label(self.fullname())
