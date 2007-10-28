# sqlhelper -- SQL helper tools
# Copyright (C) 2005-2007 Participatory Culture Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

"""Handle relations between records.

relations handle a few things: 
   * Adding join expression to tables
   * Setting up attributes on the resulting record objects.
   * OneToMany and ManyToMany relations handle updating the list
     of related records.

This module assumes that foreign keys references primary keys and are
single-columned.  Hopefully this isn't too restrictive.
"""

from sqlhelper.sql import Delete, Insert, Select, CrossJoin
from sqlhelper.orm import query

class Relation(object):
    """Base class for all relations."""

    def __init__(self, name, table, related_table):
        """Create a one-to-many relation

        Arguments:

        name -- name of the relation.  This will be the attribute that
            gets created in join().
        table -- table that the relation belongs to
        related_table -- table on the other side of the relation.
        """

        self.name = name
        self.table = table
        self.related_table = related_table
        self.reflection = None

    def set_reflection(self, other_relation):
        self.reflection = other_relation
        other_relation.reflection = self

    def add_join(self, from_expression, table, related_table):
        """Join from_expression with this relation's table and return the
        result.

        One tricky part is that tables get aliased when we build the SELECT
        statements to allow for more than 1 relation for a given table.  The
        possibly aliased tables get passed into add_join() so that we can
        join with the correct columns.
        """
        raise NotImplementedError()

    def init_record(self, record):
        """Subclasses may use this method to initialize newly created records.
        For example, OneToMany and ManyToMany create the list they use in
        do_join().
        """
        pass

    def do_join(self, record, related_record):
        """Perform the join."""
        raise NotImplementedError()

class SimpleJoiner(Relation):
    """Handles joins using a single foreign key column."""

    def add_join(self, from_expression, table, related_table):
        if self.column.table is self.table:
            fk = table.columns.get(self.column.name)
            ref = related_table.columns.get(self.column.ref.name)
            return from_expression.join(related_table, fk==ref, 'LEFT')
        else:
            fk = related_table.columns.get(self.column.name)
            ref = table.columns.get(self.column.ref.name)
            return from_expression.join(related_table, fk==ref, 'LEFT')

class ManyToOne(SimpleJoiner):
    def __init__(self, name, column):
        """Create a many-to-one relation

        Arguments:

        name -- name of the relation.  This will be the attribute that
            gets created in join().
        column -- column that defines the relationship, i.e. a foreign
            key that belongs to the table and references the related table's
            primary key.
        """
        if column.ref is None:
            raise ValueError("column is not a foreign key")
        super(ManyToOne, self).__init__(name, column.table, column.ref.table)
        self.column = column

    def init_record(self, record):
        setattr(record, self.name, None)

    def do_join(self, record, related_record):
        setattr(record, self.name, related_record)

class OneToOne(SimpleJoiner):
    def __init__(self, name, column, related_table):
        """Create a one-to-one relation

        Arguments:

        name -- name of the relation.  This will be the attribute that
            gets created in join().
        column -- column that defines the relationship, i.e. a foreign
            key that belongs to either the table or the related table.  It
            should reference the other table's primary key.
        """
        if column.ref is None:
            raise ValueError("column is not a foreign key")
        if column.table is not related_table:
            table = column.table
        else:
            table = column.ref.table
        super(OneToOne, self).__init__(name, table, related_table)
        self.column = column

    def init_record(self, record):
        setattr(record, self.name, None)

    def do_join(self, record, related_record):
        setattr(record, self.name, related_record)
        if self.reflection is not None:
            setattr(related_record, self.reflection.name, record)

class OneToMany(SimpleJoiner):
    def __init__(self, name, column):
        """Create a one-to-many relation

        Arguments:

        name -- name of the relation.  This will be the attribute that
            gets created in join().
        column -- column that defines the relation, i.e. a foreign key that
            belongs to the related table and references the table's primary
            key.
        """
        if column.ref is None:
            raise ValueError("column is not a foreign key")
        super(OneToMany, self).__init__(name, column.ref.table, column.table)
        self.column = column

    def init_record(self, record):
        setattr(record, self.name, RelationList(self, record))

    def do_join(self, record, related_record):
        result_list = getattr(record, self.name)
        result_list.records.append(related_record)
        # we might as well set the other side of the relation if we can
        if self.reflection is not None:
            setattr(related_record, self.reflection.name, record)

    def handle_list_add(self, connection, parent_record, record):
        join_value = getattr(parent_record, self.column.ref.name)
        setattr(record, self.column.name, join_value)
        record.save(connection)
        if self.reflection is not None:
            setattr(record, self.reflection.name, parent_record)

    def handle_list_remove(self, connection, parent_record, record):
        record.delete(connection)

    def handle_list_clear(self, connection, parent_record):
        join_value = getattr(parent_record, self.column.ref.name)
        delete = Delete(self.column.table)
        delete.wheres.append(self.column==join_value)
        delete.execute(connection)

class ManyToMany(Relation):
    def __init__(self, name, foreign_key, relation_fk):
        """Create a many-to-many relation

        many-to-many relations are handled with a join table that has a
        2 foreign keys.  One references the table this relation belongs to and
        the other references the related table.

        Arguments:

        name -- name of the relation.  This will be the attribute that
            gets created in join().
        foreign_key -- foreign key that references the table.
        relation_fk -- foreign key that references the related table.
        """
        if foreign_key.table is not relation_fk.table:
            msg = "foreign_key and relation_fk must be from the same table"
            raise ValueError(msg)
        super(ManyToMany, self).__init__(name, foreign_key.ref.table,
                relation_fk.ref.table)
        self.foreign_key = foreign_key
        self.relation_fk = relation_fk
        self.join_table = foreign_key.table
        self.use_exists_subquery = self._needs_exists_subquery()

    def _needs_exists_subquery(self):
        """If there can be duplicate values in the join table for our 2
        foreign keys, then we need to handle the join specially.  Simply
        joining the tables together would result in a lot of extra rows, so
        instead we use an EXISTS subquery.  (see _add_joins_with_exists()).
        """
        foreign_keys = set([self.foreign_key, self.relation_fk])
        primary_keys = set(self.join_table.primary_keys)
        return not primary_keys.issubset(foreign_keys)

    def add_join(self, from_expression, table, related_table):
        if not self.use_exists_subquery:
            return self._simple_join(from_expression, table, related_table)
        else:
            return self._exists_join(from_expression, table, related_table)

    def _simple_join(self, from_expression, table, related_table):
        join_table_alias = 'j_%s' % self.name
        join_table = self.join_table.alias(join_table_alias)
        where1 = (join_table.columns.get(self.foreign_key.name) ==
                table.columns.get(self.foreign_key.ref.name))
        where2 = (join_table.columns.get(self.relation_fk.name) ==
                related_table.columns.get(self.relation_fk.ref.name))
        tables = CrossJoin(join_table, related_table)
        return from_expression.join(tables, where1 & where2, 'LEFT')

    def _exists_join(self, from_expression, table, related_table):
        subquery = self.join_table.select('*')
        # no need to alias join_table, since it's only used in the subquery
        subquery.wheres.append(self.foreign_key ==
                table.columns.get(self.foreign_key.ref.name))
        subquery.wheres.append(self.relation_fk ==
                related_table.columns.get(self.relation_fk.ref.name))
        return from_expression.join(related_table, subquery.exists(), 
                'LEFT')

    def init_record(self, record):
        setattr(record, self.name, RelationList(self, record))

    def do_join(self, record, related_record):
        result_list = getattr(record, self.name)
        result_list.records.append(related_record)

    def handle_list_add(self, connection, parent_record, record):
        insert = Insert(self.join_table)
        parent_join_value = getattr(parent_record, self.foreign_key.ref.name)
        record_join_value = getattr(record, self.relation_fk.ref.name)
        insert.add_value(self.foreign_key.fullname(), parent_join_value)
        insert.add_value(self.relation_fk.fullname(), record_join_value)
        insert.execute(connection)

    def handle_list_remove(self, connection, parent_record, record):
        delete = Delete(self.join_table)
        parent_join_value = getattr(parent_record, self.foreign_key.ref.name)
        record_join_value = getattr(record, self.relation_fk.ref.name)
        delete.wheres.append(self.foreign_key==parent_join_value)
        delete.wheres.append(self.relation_fk==record_join_value)
        delete.execute(connection)

    def handle_list_clear(self, connection, parent_record):
        delete = Delete(self.join_table)
        parent_join_value = getattr(parent_record, self.foreign_key.ref.name)
        delete.wheres.append(self.foreign_key==parent_join_value)
        delete.execute(connection)

class RelationList(query.ResultSet):
    """List of records returned by a one-to-many/many-to-many relation.
    
    RelationLists handle updating the database when objects get added/removed
    from the list.
    """

    def __init__(self, relation, parent_record):
        self.relation = relation
        self.parent_record = parent_record
        query.ResultSet.__init__(self, relation.related_table, [])

    def add_record(self, connection, record):
        self.relation.handle_list_add(connection, self.parent_record, record)
        self.records.append(record)

    def add_records(self, connection, records):
        for record in records:
            self.add_record(connection, record)

    def remove_record(self, connection, record):
        self.records.remove(record)
        self.relation.handle_list_remove(connection, self.parent_record, record)

    def clear(self, connection):
        self.records = []
        self.relation.handle_list_clear(connection, self.parent_record)

    # Emulate a list
    def __iter__(self):
        return iter(self.records)
    def __len__(self):
        return len(self.records)
    def __getitem__(self, idx):
        return self.records[idx]
    def __repr__(self):
        return '%s: %s' % (self.__class__.__name__, repr(self.records))
