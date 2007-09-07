"""SQL statements.  

Statement objects are entire SQL statements (SELECT, INSERT, etc).  Statement
classes are basically just a containers for a bunch of Expression objects
along with a compile() method that builds the statement.  In general, you can
substitute strings instead of Expression objects if you don't need argument
quoting.

"""

import logging
import expression
from sqlhelper import signals
from sqlhelper.exceptions import SQLError, NotFoundError, TooManyResultsError

class ExpressionList(list):
    def append(self, object, *args):
        if not isinstance(object, expression.Expression):
            object = expression.Expression(object, *args)
        elif args:
            msg = "Can't specify args when passing in an Expression."
            raise ValueError(msg)
        super(ExpressionList, self).append(object)

class Statement(object):
    """Base class for SQL statements."""
    __signal__ = None

    def compile(self):
        """compile this statement into something that can be passed to the
        database.  Returns (sql, args) where sql is an sql string and args are
        arguments to use to fill in the format arguments.
        """
        raise NotImplementedError()

    def execute(self, connection):
        if self.__class__.__signal__ is not None:
            self.__class__.__signal__.emit(self)
        text, args = self.compile()
        debug_string = self.make_debug_string(text, args)
        logging.sql(debug_string)
        try:
            return connection.execute(text, args)
        except Exception, e:
            msg = "Error running %s: %s" % (debug_string, e)
            raise SQLError(msg)

    def make_debug_string(self, text, args):
        return "%s\n\nARGS: %r" % (text, args)

    def __str__(self):
        return self.make_debug_string(*self.compile())

class Select(Statement):
    """SQL SELECT statement."""

    def __init__(self, *columns):
        self.columns = ExpressionList()
        self.froms = ExpressionList()
        self.order_by = ExpressionList()
        self.group_by = ExpressionList()
        self.wheres = ExpressionList()
        self.havings = ExpressionList()
        self.limit = None
        self.offset = None
        for column in columns:
            self.columns.append(column)

    def count(self, connection):
        s = Select()
        s.columns = [expression.COUNT]
        s.froms = self.froms
        s.wheres = self.wheres
        s.havings = self.havings
        s.group_by = self.group_by
        return self.execute_scalar(connection)

    def compile(self):
        comp = StatementCompilation()
        comp.add_text("SELECT ")
        comp.add_expression_list(self.columns)
        comp.add_text("\nFROM ")
        comp.add_expression_list(self.froms)
        if self.wheres:
            comp.add_text("\nWHERE ")
            comp.add_expression(expression.and_together(self.wheres))
        if self.group_by:
            comp.add_text("\nGROUP BY ")
            comp.add_expression_list(self.group_by)
        if self.havings:
            comp.add_text("\nHAVING ")
            comp.add_expression(expression.and_together(self.havings))
        if self.order_by:
            comp.add_text("\nORDER BY ")
            comp.add_expression_list(self.order_by)
        if self.limit is not None or self.offset is not None:
            if self.offset is None:
                offset = 0
            else:
                offset = self.offset
            if self.limit is None:
                limit = 9999999
            else:
                limit = self.limit
            comp.add_text('\nLIMIT %d,%d' % (offset, limit))
        return comp.finalize()

    def subquery(self, label=None):
        text, args = self.compile()
        subquery = expression.Expression(text, *args)
        if label is not None:
            return subquery.label(label)
        return subquery

    def exists(self):
        text, args = self.compile()
        return expression.Expression("EXISTS (%s)" % text, *args)

    def execute_scalar(self, connection):
        """Execute a scalar SELECT.  This only works for selects that return a
        single column and a single row.
        """
        if len(self.columns) != 1:
            raise ValueError("execute_scalar must be called with 1 column.")
        results = self.execute(connection)
        if len(results) == 1:
            return results[0][0]
        elif len(results) == 0:
            raise NotFoundError("Row not found")
        else:
            raise TooManyResultsError("Too many rows returned")

class Insert(Statement):
    __signal__ = signals.sql_insert

    def __init__(self, table):
        self.table_name = str(table)
        self.delayed = False
        self.columns = ExpressionList()
        self.values = ExpressionList()

    def add_value(self, column, value):
        self.columns.append(column)
        self.values.append(expression.Quoted(value))

    def add_values(self, **values):
        for column, value in values.items():
            self.add_value(column, value)

    def compile(self):
        comp = StatementCompilation()
        comp.add_text('INSERT ')
        if self.delayed:
            comp.add_text('DELAYED ')
        comp.add_text('INTO %s(' % self.table_name)
        comp.add_expression_list(self.columns)
        comp.add_text(')\nVALUES(')
        comp.add_expression_list(self.values)
        comp.add_text(')')
        return comp.finalize()

class Update(Statement):
    __signal__ = signals.sql_update

    def __init__(self, table):
        self.table_name = str(table)
        self.assignments = ExpressionList()
        self.wheres = ExpressionList()
    
    def add_value(self, column, value):
        self.assignments.append(expression.Assignment(column, value))

    def add_values(self, **values):
        for column, value in values.items():
            self.add_value(column, value)

    def compile(self):
        comp = StatementCompilation()
        comp.add_text("UPDATE %s\n" % self.table_name)
        comp.add_text("SET ")
        comp.add_expression_list(self.assignments)
        if self.wheres:
            comp.add_text("\nWHERE ")
            comp.add_expression(expression.and_together(self.wheres))
        return comp.finalize()

class Delete(Statement):
    __signal__ = signals.sql_delete

    def __init__(self, table):
        self.table_name = str(table)
        self.wheres = ExpressionList()

    def compile(self):
        comp = StatementCompilation()
        comp.add_text('DELETE FROM %s\n' % self.table_name)
        if self.wheres:
            comp.add_text("\nWHERE ")
            comp.add_expression(expression.and_together(self.wheres))
        return comp.finalize()

class StatementCompilation(object):
    """Used to store parts of a SQL statement while it's being compiled."""
    def __init__(self):
        self.parts = []
        self.args = []

    def add_text(self, text):
        self.parts.append(text)

    def add_expression(self, expression):
        self.parts.append(expression.text)
        self.args.extend(expression.args)

    def add_expression_list(self, expression_list):
        self.add_expression(expression.join(expression_list, ', '))

    def finalize(self):
        return (''.join(self.parts), tuple(self.args))
