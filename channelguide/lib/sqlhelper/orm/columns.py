import logging
from sqlhelper.sql import clause

class ColumnFilterMixin(object):
    """WHERE/HAVING clause that comes from a column.  The nice thing about
    these is that they can change the column to handle aliased tables.
    """
    def __init__(self, column, string, args):
        self.column = column
        self.string = string
        self.args = args

    def compile(self):
        text = self.string.replace('##column##', self.column.fullname())
        return text, self.args

    def alias(self, aliased_table):
        self.column = aliased_table.get_column(self.column.name)

class ColumnWhere(ColumnFilterMixin, clause.Where):
    pass

class ColumnHaving(ColumnFilterMixin, clause.Having):
    pass

class ColumnStore(object):
    """Stores a bunch of columns.  Columns can be accessed as attributes, or
    by iterating through the ColumnStore object.
    """
    def __init__(self, columns=None):
        self.columns = []
        if columns is not None:
            self.add_columns(columns)

    def add_column(self, column):
        self.columns.append(column)
        setattr(self, column.name, column)

    def add_columns(self, columns):
        for column in columns:
            self.add_column(column)

    def add_to_select(self, select):
        for column in self.columns:
            column.add_to_select(select)

    def __iter__(self):
        return iter(self.columns)
    def __len__(self):
        return len(self.columns)

class ColumnBase(object):
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
        return ColumnWhere(self, string, args)

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
        if isinstance(other, ColumnBase):
            string = '##column## %s %s' % (operator, other.fullname())
            args = []
        elif isinstance(other, clause.Clause):
            string = '##column## %s %s' % (operator, other.text)
            args = other.args
        else:
            string = '##column## %s %%s' % (operator)
            args = [other]
        return self.make_filter(string, args)

    def __eq__(self, other):
        return self._sql_operator(other, '=')
    def __ne__(self, other):
        return self._sql_operator(other, '!=')
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
        string = "##column## IN (%s)" % (', '.join(percent_s))
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

class Int(ColumnBase):
    pass

class String(ColumnBase):
    def __init__(self, name, length=None, *args, **kwargs):
        ColumnBase.__init__(self, name, *args, **kwargs)
        self.length = length

    def convert_for_db(self, data):
        if (self.length is not None and data is not None and 
                len(data) > self.length):
            logging.warn("Truncating data %r for column %s", data,
                    self.fullname())
            data = data[:self.length]
        return data

class DateTime(ColumnBase):
    pass

class Boolean(ColumnBase):
    def convert_from_db(self, data):
        """Convert data coming from MySQL."""
        return bool(data)

class Subquery(ColumnBase):
    """Column that represents a SQL scalar subselect."""
    def __init__(self, name, select, *args, **kwargs):
        ColumnBase.__init__(self, name, *args, **kwargs)
        if isinstance(select, str):
            self.select_text = select
            self.select_args = []
        else:
            self.select_text, self.select_args = select.compile()

    def add_to_select(self, select):
        subquery = '(%s) AS %s' % (self.select_text, self.fullname())
        select.add_column(subquery, *self.select_args)

    def make_filter(self, string, args):
        return ColumnHaving(self, string, args)

    def fullname(self):
        if self.table is not None:
            return "%s_%s" % (self.table.name, self.name)
        else:
            return self.name

    def __str__(self):
        return str(self.subquery)
