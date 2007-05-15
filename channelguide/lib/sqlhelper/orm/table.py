from copy import copy

from relations import OneToMany, ManyToOne, ManyToMany
from exceptions import NotFoundError, TooManyResultsError
from columns import ColumnStore
import record
import query

class Table(object):
    def __init__(self, name, *columns):
        self.name = name
        self.relations = {}
        self.init_columns(columns)
        self.record_class = None

    def init_columns(self, columns):
        # ensure that non-optional columns come before optional columns.
        # Otherwile primary_key_from_row() won't work right
        self.regular_columns = [c for c in columns if not c.optional]
        self.optional_columns = [c for c in columns if c.optional]
        self.c = ColumnStore(self.regular_columns + self.optional_columns)
        self.primary_keys = []
        self.primary_key_indicies = []
        i = 0
        self.auto_increment_column = None
        for column in self.c:
            column.table = self
            if column.primary_key:
                self.primary_keys.append(column)
                self.primary_key_indicies.append(i)
            if column.auto_increment:
                if self.auto_increment_column is not None:
                    raise ValueError("Only 1 auto-increment column allowed")
                else:
                    self.auto_increment_column = column
            i += 1

    def query(self):
        return query.Query(self)

    def __str__(self):
        return self.name

    def concrete_columns(self):
        return [c for c in self.c if c.is_concrete()]

    def primary_key_from_row(self, row):
        return tuple(row[i] for i in self.primary_key_indicies)

    def find_foreign_key(self, other_table):
        """Find a foreign key column in this table that references a column in
        other_table.  If no matches or multiple matches are found ValueError
        will be thrown.
        """

        matches = []
        for column in self.c:
            if column.ref and column.ref.table is other_table:
                matches.append(column)
        if len(matches) == 1:
            return matches[0]
        elif len(matches) == 0:
            raise ValueError("No foreign keys found")
        else:
            raise ValueError("Multiple foreign keys found")

    def many_to_one(self, name, other_table, backref=None, join_column=None):
        """Add a many-to-one relation from this table to another table.

        In the normal case, when there is one foreign key from this table to
        the other table this method will find that key and use it
        automatically.  
        
        If there are multiple foreign keys, then the column to use must be
        explicitly given with the join_column parameter.

        backref creates a one_to_many relation in the other table that is the
        reflection of this one.
        """
        if join_column is None:
            join_column = self.find_foreign_key(other_table)

        if name is not None:
            self.relations[name] = ManyToOne(name, join_column)
        if backref is not None:
            other_table.relations[backref] = OneToMany(backref, join_column)

    def one_to_many(self, name, other_table, backref=None, join_column=None):
        """Add a one-to-many relation from this table to another table.

        This works in the reverse of many_to_one().  Note, the join column
        will be a column in the other table that references a column in this
        table.
        """
        other_table.many_to_one(backref, self, backref=name)

    def many_to_many(self, name, other_table, join_table, backref=None):
        """Add a many-to-many relation from this table to another table.

        join_table is a table that maps this table to the other table.  It
        should have a foreign key referencing a column in this table and one
        referencing a column in the other table.  For example:

        foo = Table('foo', Int('id'), ...)
        bar = Table('bar', Int('id'), ...)
        foo_map Table('foo_map', Int('foo_id', fk=foo.id),
            Int('bar_id', fk=bar.id))

        foo.many_to_many('bars', bar, foo_map, backref='foos')
        """

        join_column = join_table.find_foreign_key(self)
        other_join_column = join_table.find_foreign_key(other_table)

        self.relations[name] = ManyToMany(name, join_column, other_join_column)
        if backref is not None:
            other_table.relations[backref] = \
                    ManyToMany(backref, other_join_column, join_column)
