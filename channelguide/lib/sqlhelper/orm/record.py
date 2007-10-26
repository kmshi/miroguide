from itertools import izip

from sqlhelper import sql, signals, util
from sqlhelper.exceptions import NotFoundError, TooManyResultsError
from sqlhelper.orm import query
from sqlhelper.orm.relations import ManyToOne, OneToOne
from sqlhelper.sql import expression

class RecordMetaclass(type):
    """Metaclass for Record objects.  
    
    I tried to keep this as simple as possible, to avoid a lot of magic.  It
    cheks for the "table" attribute, and if it's present it does 2 things:

    * Set makes the "c" attribute be an reference to table.columns
    * Sets table.record_class
    """

    def __init__(cls, name, bases, dict):
        try:
            table = dict['table']
        except KeyError:
            pass
        else:
            if not table.primary_keys:
                msg = "Can't create Records for tables without a primary key."
                raise ValueError(msg)
            cls.c = table.c
            table.record_class = cls

class Record(object):
    """Base class for Record objects.  A Record represents a single row from
    a table.  

    Subclasses must define a class attribute called table that refrences a
    Table object.

    Record classes have a class attribute named "c" that provides easy access
    to the columns of its table.  The "c" object will have an attribute for
    each column and the attribute name will be the name of the column.  For
    example, if a record's table contains the column, Column("foo", Int),
    then c.foo will reference it.

    NOTE:  when a Record comes from the database.  __init__ isn't called.  The
    idea is that fetching an object from the database is more like unpickling
    it, than constructing a new one.  If you want code to be run when a record
    comes is fetched from the database either use __new__ or on_restore().

    Also, records that exist in the database, either because they were fetched
    from the database, or because save() was called have an attribute rowid.
    rowid is the list of primary key values for the DB row that this record
    came from.  
    """

    __metaclass__ = RecordMetaclass

    def on_restore(self):
        """Can be overriden by subclasses to handle restoring a record from
        the database.
        """
        pass

    def exists_in_db(self):
        return hasattr(self, 'rowid')

    def save(self, connection):
        self.set_foreign_keys_from_relations()
        if self.exists_in_db():
            self.update(connection)
        else:
            self.insert(connection)

    def set_foreign_keys_from_relations(self):
        for relation in self.table.relations.values():
            try:
                related_record = getattr(self, relation.name)
            except AttributeError:
                continue
            if ((isinstance(relation, ManyToOne) or
                (isinstance(relation, OneToOne) and 
                relation.column.table is self.table)) and
                not hasattr(self, relation.column.name)):
                try:
                    value = getattr(related_record, relation.column.ref.name)
                except AttributeError:
                    # the related record doesn't have a value for this column
                    # either
                    continue
                setattr(self, relation.column.name, value)

    def set_column_defaults(self):
        for column in self.table.concrete_columns():
            if not hasattr(self, column.name):
                if column.default is None and column.auto_increment:
                    # Let the database handle this column, we'll set the
                    # attribute after the insert.
                    continue
                if hasattr(column.default, '__call__'):
                    setattr(self, column.name, column.default())
                else:
                    setattr(self, column.name, column.default)

    def run_column_onupdates(self):
        for column in self.table.concrete_columns():
            if column.onupdate is not None:
                setattr(self, column.name, column.onupdate())

    def insert(self, connection):
        signals.record_insert.emit(self)
        insert = self.table.insert()
        self.set_column_defaults()
        self.add_values_to_saver(insert)
        insert.execute(connection)
        if self.table.auto_increment_column is not None:
            attr_name = self.table.auto_increment_column.name
            setattr(self, attr_name, connection.lastrowid)
        self.rowid = self.primary_key_values()

    def update(self, connection):
        signals.record_update.emit(self)
        update = self.table.update()
        update.wheres.append(self.rowid_where())
        self.run_column_onupdates()
        self.add_values_to_saver(update)
        update.execute(connection)
        self.rowid = self.primary_key_values()

    def add_values_to_saver(self, saver):
        for column in self.table.concrete_columns():
            if column.auto_increment and not hasattr(self, column.name):
                continue
            data = column.convert_for_db(getattr(self, column.name))
            saver.add_value(column.fullname(), data)
            # if the conversion changed the data, reflect that in our
            # attributes.
            setattr(self, column.name, data)

    def delete(self, connection):
        signals.record_delete.emit(self)
        delete = self.table.delete()
        delete.wheres.append(self.rowid_where())
        delete.execute(connection)
        del self.rowid

    def delete_if_exists(self, connection):
        if self.exists_in_db():
            self.delete(connection)

    @classmethod
    def query(cls, *where_args, **where_kwargs):
        retval = query.Query(cls.table)
        retval.where(*where_args, **where_kwargs)
        return retval

    @classmethod
    def get(cls, connection, id, load=None, join=None):
        retval = query.Query(cls.table)
        if load is not None:
            retval.load(*util.ensure_list(load))
        if join is not None:
            retval.join(*util.ensure_list(join))
        try:
            return retval.get(connection, id)
        except NotFoundError:
            raise NotFoundError("Record with id %s not found" % (id,))
        except TooManyResultsError:
            raise TooManyResultsError("Too many records with id %s" % (id,))

    def primary_key_values(self):
        return tuple(getattr(self, c.name) for c in self.table.primary_keys)

    def rowid_where(self):
        wheres = []
        for column, value in izip(self.table.primary_keys, self.rowid):
            wheres.append(column==value)
        return sql.and_together(wheres)

    def join(self, *relation_names):
        relation_names = [name for name in relation_names \
                if not hasattr(self, name) ]
        me_list = query.ResultSet(self.__class__.table, [self])
        return me_list.join(*relation_names)
