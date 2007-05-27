"""expression.py -- SQL expressions

Expresions objects are pieces of SQL code.  Expressions have 2 attributes,
text and args.  text is the SQL code as a string.  text can have printf-style
format strings, which will be filled in with args.  sqlhelper never actually
touches args, they get passed to the database to ensure they get properly
quoted.

sqlhelper is very liberal about operations on expressions.  It will happily
multiply a join expression with an assignment expression if you tell it to.
"""

class Expression(object):
    def __init__(self, text, *args):
        self.text = text
        self.args = args

    def __str__(self):
        return "%s ARGS: %r" % (self.text, self.args)

    # format string used to format this expression when combining it with
    # other expressions.  For most expressions this should be '(%s)', but some
    # expressions leave out the parentheses.
    combine_format = '(%s)'

    def join(self, other, on, type='INNER'):
        return Join(self, other, on, type)

    def label(self, name):
        return Label(self, name)

    def combine(self, other, operator):
        if not isinstance(other, Expression):
            other = Quoted(other)
        text_parts = []
        text_parts.append(self.combine_format % self.text)
        text_parts.append(' %s ' % operator)
        text_parts.append(other.combine_format % other.text)
        text = ''.join(text_parts)
        args = list(self.args) + list(other.args)
        return Expression(text, *args)

    def rcombine(self, other, operator):
        if not isinstance(other, expression):
            other = Quoted(other)
        return other.combine(self, operator)

    def __add__(self, other): return self.combine(other, '+')
    def __sub__(self, other): return self.combine(other, '-')
    def __mul__(self, other): return self.combine(other, '*')
    def __div__(self, other): return self.combine(other, '/')
    def __mod__(self, other): return self.combine(other, '%')
    def __and__(self, other): return self.combine(other, 'AND')
    def __or__(self, other): return self.combine(other, 'OR')

    def __radd__(self, other): return self.rcombine(other, '+')
    def __rsub__(self, other): return self.rcombine(other, '-')
    def __rmul__(self, other): return self.rcombine(other, '*')
    def __rdiv__(self, other): return self.rcombine(other, '/')
    def __rmod__(self, other): return self.rcombine(other, '%')
    def __rand__(self, other): return self.rcombine(other, 'AND')
    def __ror__(self, other): return self.rcombine(other, 'OR')

    def __lt__(self, other): return self.combine(other, '<')
    def __le__(self, other): return self.combine(other, '<=')
    def __eq__(self, other): return self.combine(other, '=')
    def __ne__(self, other): return self.combine(other, '<>')
    def __gt__(self, other): return self.combine(other, '>')
    def __ge__(self, other): return self.combine(other, '>=')

    def negate(self):
        return self.__class__('NOT (%s)' % self.text, self.args)

    def is_(self, other):
        return self.combine(other, 'IS')

    def is_not(self, other):
        return self.combine(other, 'IS NOT')

    def like(self, other):
        return self.combine(other, 'LIKE')

    def in_(self, possible_values):
        percent_s = ['%s' for i in xrange(len(possible_values))]
        text = "%s IN (%s)" % (self.text, ', '.join(percent_s))
        args = list(self.args) + list(possible_values)
        return Expression(text, *args)


def join(expressions, join_string):
    text = join_string.join(e.text for e in expressions)
    args = []
    for expression in expressions:
        args.extend(expression.args)
    return Expression(text, *args)

def combine_group(terms, operator):
    if len(terms) == 0:
        raise ValueError("Need at least 1 term")
    elif len(terms) == 1:
        if isinstance(terms[0], Expression):
            return terms[0]
        else:
            return Quoted(terms[0])
    else:
        text_parts = []
        combined_args = []
        for term in terms:
            if not isinstance(term, Expression):
                term = Quoted(term)
            text_parts.append(term.combine_format % term.text)
            combined_args.extend(term.args)
        joiner = ' %s ' % operator
        return Expression(joiner.join(text_parts), *combined_args)

def and_together(terms):
    return combine_group(terms, 'AND')

def or_together(terms):
    return combine_group(terms, 'OR')

def sum(terms):
    return combine_group(terms, '+')

def product(terms):
    return combine_group(terms, '*')

class SimpleExpression(Expression):
    """SimpleExpression is exactly the same as Expression, except it doesn't
    get parentheses when it's combined with other Expressions.
    """
    combine_format = '%s'

class Quoted(SimpleExpression):
    def __init__(self, value):
        super(Quoted, self).__init__('%s', value)

class Literal(SimpleExpression):
    def __init__(self, value):
        super(Literal, self).__init__(value)

class CompoundExpression(Expression):
    """Expression that is made up from other expressions."""

    def __init__(self, format_string, *args):
        """Create a compound expression.  format_string is a printf-style
        string to use to create the expression.  args be other Expression
        objects or any python objects.  

        NOTE: non-Expression objects passed in as args won't get quoted.
        """
        self.args = []
        format_args = []
        for obj in args:
            if isinstance(obj, Expression):
                format_args.append(obj.text)
                self.args.extend(obj.args)
            else:
                format_args.append(obj)
        self.text = format_string % tuple(format_args)

class Label(CompoundExpression):
    def __init__(self, expression, name):
        super(Label, self).__init__('(%s) AS %s', expression, name)

class OrderBy(CompoundExpression):
    """ORDER BY expression."""

    def __init__(self, expression, desc=False):
        if desc:
            super(OrderBy, self).__init__('%s DESC', expression)
        else:
            super(OrderBy, self).__init__('%s', expression)

class Join(CompoundExpression):
    """SQL JOIN expression.  For example:
    bar LEFT JOIN foo on foo.id = bar.foo_id
    """
    def __init__(self, table, join, on, type='INNER'):
        if isinstance(join, Expression):
            format_string = "%%s %%s JOIN %s ON %%s" % join.combine_format
        else:
            format_string = "%s %s JOIN %s ON %s"
        super(Join, self).__init__(format_string, table, type, join, on)

class CrossJoin(CompoundExpression):
    """SQL CROSS JOIN expression.  For example:

    foo CROSS JOIN bar CROSS JOIN booya.
    """

    def __init__(self, *tables):
        expressions = []
        for table in tables:
            if isinstance(table, Expression):
                expressions.append(table)
            else:
                expressions.append(Literal(table))
        joined = join(expressions, ' CROSS JOIN ')
        self.text = joined.text
        self.args = joined.args

class Assignment(CompoundExpression):
    def __init__(self, name, value):
        if not isinstance(value, Expression):
            value = Quoted(value)
        super(Assignment, self).__init__('%s=%s', name, value)

NOW = Literal("NOW()")
COUNT = Literal("COUNT(*)")
RAND = Literal("RAND()")
NULL = Literal("NULL")
