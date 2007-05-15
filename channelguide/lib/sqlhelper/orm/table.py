"""table.py -- contains classes to model SQL tables.

Tables store a set of columns that belong to them.  columns for a table can be
accessed using the columns attribute, which is a ColumnStore object.  The
attribute "c" is a shorthand for columns.  For example:

foo = Table('foo', 
    columns.Int('id', primary_key=True), 
    columns.String('name', 255))

The 'id' column can be accessed by foo.c.id (or foo.columns[0], foo.c[0],
etc).
"""

from sqlhelper.sql import Select
from relations import OneToMany, ManyToOne, ManyToMany, OneToOne
from columns import ColumnStore, Subselect

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
        self.columns = ColumnStore(self.regular_columns + self.optional_columns)
        self.c = self.columns
        self.primary_keys = []
        self.primary_key_indicies = []
        i = 0
        self.auto_increment_column = None
        for column in self.columns:
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

    def __str__(self):
        return self.name

    def concrete_columns(self):
        return [c for c in self.columns if c.is_concrete()]

    def make_count_column(self, name, other_table, optional=True, *extra_wheres):
        count_select = Select()
        count_select.add_column("COUNT(*)")
        count_select.add_from(other_table.name)
        join_column = self.find_foreign_key(other_table, search_reverse=True)
        count_select.add_where(join_column==join_column.ref)
        for where in extra_wheres:
            count_select.add_where(where)
        column = Subselect(name, count_select, optional=optional)
        column.table = self
        return column

    def add_count_column(self, *args, **kwargs):
        self.columns.add_column(self.make_count_column(*args, **kwargs))

    def primary_key_from_row(self, row):
        return tuple(row[i] for i in self.primary_key_indicies)

    def _find_all_foreign_keys(self, other_table):
        return [col for col in self.columns \
                if col.ref and col.ref.table is other_table]

    def find_foreign_key(self, other_table, search_reverse=False):
        """Find a foreign key column in this table that references a column in
        other_table.  If search_reverse is True, then this method will also
        look for foreign keys in other_table that reference this table.  If no
        matches or multiple matches are found ValueError will be thrown.
        """

        foreign_keys = self._find_all_foreign_keys(other_table)
        if search_reverse:
            foreign_keys += other_table._find_all_foreign_keys(self)
        if len(foreign_keys) == 1:
            return foreign_keys[0]
        elif len(foreign_keys) == 0:
            raise ValueError("No foreign keys found")
        else:
            raise ValueError("Multiple foreign keys found")

    def many_to_one(self, name, other_table, backref=None, join_column=None):
        """Add a many-to-one relation from this table to another table.

        In the normal case, when there is one foreign key from table to
        other_table this method will find that key and use it automatically.
        If there are multiple foreign keys, then the column to use must be
        explicitly given with the join_column parameter.

        backref creates a one_to_many relation in the other table that is the
        reflection of this one.
        """
        if join_column is None:
            join_column = self.find_foreign_key(other_table)

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

    def one_to_one(self, name, other_table, backref=None, join_column=None):
        """Add a one-to-one relation from this table to another table.

        A one to one relation stems from a foreign key that is also a unique
        or prime key.  For example:

        foo = Table('foo', columns.Int('id', primary_key=True), ...)
        foo_extra = Table('foo_extra', 
            columns.Int('id', primary_key=True, fk=foo.c.id), 
            ...)

        Note: the name of this relation is slightly misleading.  It's more
        precicely, one-to-one-or-zero.  For example, for each row in
        foo_extra, there is a corresponding row in foo, but for each foo there
        can be 0 or 1 foo_extra rows.

        one_to_one can be called on either table that is part of the relation.  

        In the normal case, when there is one foreign key between table
        and other_table this method will find that key and use it
        automatically.  If there are multiple foreign keys, then the column to
        use must be explicitly given with the join_column parameter.

        backref creates a one_to_one relation in the other table that is the
        reflection of this one.
        """
        if join_column is None:
            join_column = self.find_foreign_key(other_table, 
                    search_reverse=True)
        self.relations[name] = OneToOne(name, join_column, other_table)
        if backref is not None:
            other_table.relations[backref] = OneToOne(backref, join_column,
                    self)

