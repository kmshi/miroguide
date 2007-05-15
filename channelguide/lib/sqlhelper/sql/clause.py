class Clause(object):
    def __init__(self, text, args):
        self.text = text
        self.args = args

    def __str__(self):
        return "%s ARGS: %r" % (self.text, self.args)

class Value(Clause):
    def __init__(self, value):
        self.text = '%s'
        self.args = [value]

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
    def _and_or_together(cls, terms, operator):
        if len(terms) == 1:
            return terms[0]
        text, args = join_clauses(terms, ' %s ' % operator, conversion='(%s)')
        return cls(text, args)

    @classmethod
    def and_together(cls, terms):
        return cls._and_or_together(terms, 'AND')

    @classmethod
    def or_together(cls, terms):
        return cls._and_or_together(terms, 'OR')

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

class Join(Clause):
    """SQL JOIN clause."""
    def __init__(self, table, on, type='INNER'):
        self.text = "%s JOIN %s ON %s" % (type, table, on.text)
        self.args = on.args

class MultiJoin(Join):
    def __init__(self, tables, on, type='INNER'):
        table = '(%s)' % (' CROSS JOIN '.join(str(t) for t in tables))
        Join.__init__(self, table, on, type)

class Set(Clause):
    def __init__(self, name, value):
        self.text = "%s=%%s" % name
        self.args = [value]

def join_clauses(clause_list, join_string, conversion=None):
    if conversion is None:
        parts = [c.text for c in clause_list]
    else:
        parts = [conversion % c.text for c in clause_list]
    text = join_string.join(parts)
    args = []
    for clause in clause_list:
        args.extend(clause.args)
    return text, args
