"""SQL statements.  

Most of the Statement subclasses are just a container for lists of Clause
objects with a compile() method that builds the statement.  In general, they
can be altered in several ways:
  - Adding Clause objects to the lists directory:
     select.wheres.append(WhereClause('foo.id=%s', 123456)
  - By using a helper method, that builds the clause for you:
     select.add_where('foo.id=%s', 123456)
  - You can usually use the helper method to add the clause as well:
     select.add_where(WhereClause('foo.id=%s', 123456))

"""

import logging
import clause
from exceptions import SQLError
from sqlhelper import signals

class Statement(object):
    """Base class for SQL statements."""
    __signal__ = None

    def compile(self):
        """compile this statement into something that can be passed to the
        database.  Returns (sql, args) where sql is an sql string and args are
        arguments to use to fill in the format arguments.
        """
        raise NotImplementedError()

    def execute(self, cursor):
        if self.__class__.__signal__ is not None:
            self.__class__.__signal__.emit(self)
        text, args = self.compile()
        debug_string = self.make_debug_string(text, args)
        logging.sql(debug_string)
        try:
            cursor.execute(text, args)
        except Exception, e:
            msg = "Error running %s: %s" % (debug_string, e)
            raise SQLError(msg)

    def ensure_clause(self, clause_class, clause_arg, args):
        if isinstance(clause_arg, clause.Clause):
            if not args:
                return clause_arg
            else:
                raise ValueError("Can't specify args when passing in a "
                        "Clause object")
        else:
            return clause_class(str(clause_arg), args)

    def make_debug_string(self, text, args):
        return "%s\n\nARGS: %r" % (text, args)

    def __str__(self):
        text, args = self.compile()
        return self.make_debug_string(text, args)

class Select(Statement):
    """SQL SELECT statement."""

    def __init__(self, *columns):
        self.columns = []
        self.froms = []
        self.wheres = []
        self.havings = []
        self.joins = []
        self.order_by = None
        self.limit = None
        self.offset = None
        for column in columns:
            self.add_column(column)

    def add_column(self, column, *args):
        self.columns.append(self.ensure_clause(clause.Column, column, args))

    def add_columns(self, *columns):
        for column in columns:
            self.add_column(column)

    def add_from(self, table, *args):
        self.froms.append(self.ensure_clause(clause.Table, table, args))

    def add_where(self, where, *args):
        self.wheres.append(self.ensure_clause(clause.Where, where, args))

    def add_having(self, having, *args):
        self.havings.append(self.ensure_clause(clause.Having, having, args))

    def add_join(self, table, on, type='INNER'):
        if not hasattr(table, '__iter__'):
            self.joins.append(clause.Join(table, on, type))
        else:
            self.joins.append(clause.MultiJoin(table, on, type))

    def count(self, cursor):
        s = Select()
        s.add_columns('COUNT(*)')
        s.froms = self.froms
        s.wheres = self.wheres
        return s.execute(cursor)[0][0]

    def compile(self):
        comp = StatementCompilation()
        comp.add_text("SELECT ")
        comp.join_clauses(self.columns, ', ')
        comp.add_text("\nFROM ")
        comp.join_clauses(self.froms, ', ')
        comp.add_text("\n")
        comp.add_clauses(self.joins)
        comp.add_where_list(self.wheres)
        comp.add_having_list(self.havings)
        if self.order_by is not None:
            comp.add_text("ORDER BY ")
            if isinstance(self.order_by, clause.Clause):
                comp.add_clause(self.order_by)
            else:
                comp.add_text(self.order_by)
            comp.add_text('\n')
        if self.limit is not None or self.offset is not None:
            if self.offset is None:
                offset = 0
            else:
                offset = self.offset
            if self.limit is None:
                limit = 9999999
            else:
                limit = self.limit
            comp.add_text('LIMIT %s,%s\n', offset, limit)
        return comp.finalize()

    def as_subquery(self, name):
        return clause.Subquery(self, name)

    def as_exists(self):
        text, args = self.compile()
        return clause.Where("EXISTS (%s)" % text, args)

    def execute(self, cursor):
        Statement.execute(self, cursor)
        return cursor.fetchall()

class Insert(Statement):
    __signal__ = signals.sql_insert

    def __init__(self, table):
        self.table = table
        self.columns = []
        self.values = []

    def add_value(self, column, value):
        self.columns.append(clause.Column(column))
        self.values.append(clause.Value(value))

    def compile(self):
        comp = StatementCompilation()
        comp.add_text('INSERT INTO %s(' % self.table)
        comp.join_clauses(self.columns, ', ')
        comp.add_text(')\nVALUES(')
        comp.join_clauses(self.values, ', ')
        comp.add_text(')')
        return comp.finalize()

class Update(Statement):
    __signal__ = signals.sql_update

    def __init__(self, table):
        self.table = table
        self.sets = []
        self.wheres = []
    
    def add_value(self, column, value):
        self.sets.append(self.ensure_clause(clause.Set, column, value))

    def add_where(self, where, *args):
        self.wheres.append(self.ensure_clause(clause.Where, where, args))

    def compile(self):
        comp = StatementCompilation()
        comp.add_text("UPDATE %s\n" % self.table)
        comp.add_text("SET ")
        comp.join_clauses(self.sets, ', ')
        comp.add_text("\n")
        comp.add_where_list(self.wheres)
        return comp.finalize()

class Delete(Statement):
    __signal__ = signals.sql_delete

    def __init__(self, table):
        self.table = table
        self.wheres = []

    def add_where(self, where, *args):
        self.wheres.append(self.ensure_clause(clause.Where, where, args))
    
    def compile(self):
        comp = StatementCompilation()
        comp.add_text('DELETE FROM %s\n' % self.table)
        comp.add_where_list(self.wheres)
        return comp.finalize()

class StatementCompilation(object):
    """Used to store parts of a SQL statement while it's being compiled."""
    def __init__(self):
        self.parts = []
        self.args = []

    def add_text(self, text, *args):
        self.parts.append(text)
        self.args.extend(args)

    def add_clause(self, clause):
        self.add_text(clause.text, *clause.args)

    def add_clauses(self, clauses, with_newlines=True):
        for clause in clauses:
            self.add_text(clause.text, *clause.args)
            if with_newlines:
                self.add_text("\n")

    def join_clauses(self, clause_list, join_string, conversion=None):
        text, args = clause.join_clauses(clause_list, join_string, conversion)
        self.add_text(text, *args)

    def finalize(self):
        return (''.join(self.parts), self.args)

    def add_filter_list(self, filter_class, filters):
        if len(filters) == 0:
            return
        elif len(filters) == 1:
            combined = filters[0]
        else:
            combined = filter_class.and_together(filters)
        self.parts.append('%s %s\n' % (filter_class.clause_string, 
            combined.text))
        self.args.extend(combined.args)

    def add_where_list(self, wheres):
        self.add_filter_list(clause.Where, wheres)

    def add_having_list(self, havings):
        self.add_filter_list(clause.Having, havings)
