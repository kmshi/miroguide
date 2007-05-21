class Clause(object):
    def __init__(self, text, args=None):
        self.text = text
        if args is None:
            args = []
        self.args = args

    def compile(self):
        """Return a string and a set of format arguments that represents this
        clause.

        Subclasses may override this to provide more complex behaviour.
        """

        return self.text, self.args

    def __str__(self):
        text, args = self.compile()
        return "%s ARGS: %r" % (self.text, self.args)

class Value(Clause):
    """Value that gets quoted by the database."""

    def __init__(self, value):
        self.text = '%s'
        self.args = [value]

class Literal(Clause):
    """Value that we avoid quoting by the database."""
    def __init__(self, value):
        self.text = str(value)
        self.args = []

class Column(Clause):
    """Column in a SELECT statement."""

class Subquery(Clause):
    """Subquery column."""
    def __init__(self, select, name):
        select_text, self.args = select.compile()
        self.text = '(%s) AS %s' % (select_text, name)

class Table(Clause):
    """Table in a SELECT statement."""

class Filter(Clause):
    """Base class for WHERE and HAVING clauses."""

    @classmethod
    def _and_or_together(cls, operator, terms):
        if len(terms) == 1:
            return terms[0]
        else:
            text, args = join_clauses(terms, ' %s ' % operator,
                    conversion='(%s)')
            return cls(text, args)

    @classmethod
    def and_together(cls, terms):
        return cls._and_or_together('AND', terms)

    @classmethod
    def or_together(cls, terms):
        return cls._and_or_together('OR', terms)

    def __and__(self, other):
        return self.__class__.and_together((self, other))
    
    def __or__(self, other):
        return self.__class__.or_together((self, other))

class Where(Filter):
    """SQL WHERE clause."""
    clause_string = 'WHERE'

class Having(Filter):
    """SQL HAVING clause."""
    clause_string = 'HAVING'

class OrderBy(Clause):
    """ORDER BY clause."""
    def __init__(self, column, desc=False):
        self.text = str(column)
        if desc:
            self.text += ' DESC'
        self.args = []

class Join(Clause):
    """SQL JOIN clause."""
    def __init__(self, table, on, type='INNER'):
        self.table = table
        self.on = on
        self.type = type

    def compile(self):
        on_text, on_args = self.on.compile()
        text = "%s JOIN %s ON %s" % (self.type, self.table, on_text)
        return text, on_args

class MultiJoin(Join):
    def __init__(self, tables, on, type='INNER'):
        table = '(%s)' % (' CROSS JOIN '.join(str(t) for t in tables))
        Join.__init__(self, table, on, type)

class JoinedTable(Table):
    """Table joined to other tables.  For example:
    "foo JOIN bar ON bar.foo_id=foo.id"
    """
    def __init__(self, table, *joins):
        join_text, join_args = join_clauses(joins, ' ')
        self.text = '%s %s' % (table, join_text)
        self.args = join_args

class Set(Clause):
    def __init__(self, name, value):
        self.text = "%s=%%s" % name
        self.args = [value]

def join_clauses(clause_list, join_string, conversion=None):
    compiled = [clause.compile() for clause in clause_list]
    if conversion is None:
        parts = [c[0] for c in compiled]
    else:
        parts = [conversion % c[0] for c in compiled]
    joined_text = join_string.join(parts)
    joined_args = []
    for text, args in compiled:
        joined_args.extend(args)
    return joined_text, joined_args

NOW = Literal("NOW()")
COUNT = Literal("COUNT(*)")
RAND = Literal("RAND()")
