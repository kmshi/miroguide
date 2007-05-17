"""Handle relations between records.

relations handle a few things: 
   * Adding join clauses to sql select statements 
   * Setting up attributes on the resulting record objects.
   * OneToMany and ManyToMany relations handle updating the list
     of related records.

This module assumes that foreign keys references primary keys and are
single-columned.  Hopefully this isn't too restrictive.
"""

from sqlhelper.sql import Delete, Insert, Select

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

    def add_joins(self, select, table, related_table):
        """Add joins to a Select object so that this relation's table is
        included in the result.

        One tricky part is that tables get aliased when we build the SELECT
        statements to allow for more than 1 relation for a given table.  The
        possibly aliased tables get passed into add_joins() so that we can
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

    def add_joins(self, select, table, related_table):
        if self.column.table is self.table:
            fk = table.get_column(self.column.name)
            ref = related_table.get_column(self.column.ref.name)
            select.add_join(related_table, fk==ref)
        else:
            fk = related_table.get_column(self.column.name)
            ref = table.get_column(self.column.ref.name)
            select.add_join(related_table, fk==ref, 'LEFT')

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

class NToManyMixin(object):
    """Mixin for one-to-many and many-to-many relations."""

    def init_record(self, record):
        setattr(record, self.name, RelationList(self, record))

    def do_join(self, record, related_record):
        result_list = getattr(record, self.name)
        result_list.records.append(related_record)

class OneToMany(NToManyMixin, SimpleJoiner):
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

    def handle_list_add(self, cursor, parent_record, record):
        join_value = getattr(parent_record, self.column.ref.name)
        setattr(record, self.column.name, join_value)
        record.save(cursor)

    def handle_list_remove(self, cursor, parent_record, record):
        record.delete(cursor)

    def handle_list_clear(self, cursor, parent_record):
        join_value = getattr(parent_record, self.column.ref.name)
        delete = Delete(self.column.table)
        delete.wheres.append(self.column==join_value)
        delete.execute(cursor)

class ManyToMany(NToManyMixin, Relation):
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

    def add_joins(self, select, table, related_table):
        if not self.use_exists_subquery:
            self._add_joins_simple(select, table, related_table)
        else:
            self._add_joins_with_exists(select, table, related_table)

    def _add_joins_simple(self, select, table, related_table):
        join_table_alias = 'j_%s' % self.name
        join_table = self.join_table.alias(join_table_alias)
        where1 = (join_table.get_column(self.foreign_key.name) ==
                table.get_column(self.foreign_key.ref.name))
        where2 = (join_table.get_column(self.relation_fk.name) ==
                related_table.get_column(self.relation_fk.ref.name))
        select.add_join((join_table, related_table), where1 & where2, 'LEFT')

    def _add_joins_with_exists(self, select, table, related_table):
        subquery = Select()
        subquery.add_column('*')
        # no need to alias join_table, since it's only used in the subquery
        subquery.add_from(self.join_table.name)
        subquery.add_where(self.foreign_key ==
                table.get_column(self.foreign_key.ref.name))
        subquery.add_where(self.relation_fk ==
                related_table.get_column(self.relation_fk.ref.name))
        select.add_join(related_table, subquery.as_exists(), 'LEFT')

    def handle_list_add(self, cursor, parent_record, record):
        insert = Insert(self.join_table)
        parent_join_value = getattr(parent_record, self.foreign_key.ref.name)
        record_join_value = getattr(record, self.relation_fk.ref.name)
        insert.add_value(self.foreign_key.fullname(), parent_join_value)
        insert.add_value(self.relation_fk.fullname(), record_join_value)
        insert.execute(cursor)

    def handle_list_remove(self, cursor, parent_record, record):
        delete = Delete(self.join_table)
        parent_join_value = getattr(parent_record, self.foreign_key.ref.name)
        record_join_value = getattr(record, self.relation_fk.ref.name)
        delete.wheres.append(self.foreign_key==parent_join_value)
        delete.wheres.append(self.relation_fk==record_join_value)
        delete.execute(cursor)

    def handle_list_clear(self, cursor, parent_record):
        delete = Delete(self.join_table)
        parent_join_value = getattr(parent_record, self.foreign_key.ref.name)
        delete.wheres.append(self.foreign_key==parent_join_value)
        delete.execute(cursor)

class RelationList(object):
    """List of records returned by a one-to-many/many-to-many relation.
    
    RelationLists handle updating the database when objects get added/removed
    from the list.
    """

    def __init__(self, relation, parent_record):
        self.relation = relation
        self.parent_record = parent_record
        self.records = []

    def add_record(self, cursor, record):
        self.relation.handle_list_add(cursor, self.parent_record, record)
        self.records.append(record)

    def add_records(self, cursor, records):
        for record in records:
            self.add_record(cursor, record)

    def remove_record(self, cursor, record):
        self.records.remove(record)
        self.relation.handle_list_remove(cursor, self.parent_record, record)

    def clear(self, cursor):
        self.records = []
        self.relation.handle_list_clear(cursor, self.parent_record)

    # Emulate a list
    def __iter__(self):
        return iter(self.records)
    def __len__(self):
        return len(self.records)
    def __getitem__(self, idx):
        return self.records[idx]
    def __repr__(self):
        return '%s: %s' % (self.__class__.__name__, repr(self.records))
