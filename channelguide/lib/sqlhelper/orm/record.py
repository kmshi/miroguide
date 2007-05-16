from itertools import izip

from exceptions import NotFoundError, TooManyResultsError
from sqlhelper import sql
from sqlhelper.orm import query
from sqlhelper.sql import clause

def ensure_list(obj):
    if hasattr(obj, '__iter__'):
        return obj
    else:
        return [obj]

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

    Records have a single attribute: rowid.  rowid is the list of primary key
    values for the DB row that this record came from, or None if the record
    didn't come from the database.
    """

    __metaclass__ = RecordMetaclass

    def __init__(self):
        self.rowid=None

    def exists_in_db(self):
        return self.rowid is not None

    def save(self, cursor):
        if self.exists_in_db():
            self.update(cursor)
        else:
            self.insert(cursor)

    def set_column_defaults(self):
        for column in self.table.concrete_columns():
            if not hasattr(self, column.name):
                if hasattr(column.default, '__call__'):
                    setattr(self, column.name, column.default())
                else:
                    setattr(self, column.name, column.default)

    def run_column_onupdates(self):
        for column in self.table.concrete_columns():
            if column.onupdate is not None:
                setattr(self, column.name, column.onupdate())

    def insert(self, cursor):
        insert = sql.Insert(self.table)
        self.set_column_defaults()
        self.add_values_to_saver(insert)
        insert.execute(cursor)
        if self.table.auto_increment_column is not None:
            attr_name = self.table.auto_increment_column.name
            setattr(self, attr_name, cursor.lastrowid)
        self.rowid = self.primary_key_values()

    def update(self, cursor):
        update = sql.Update(self.table)
        update.wheres.append(self.rowid_where())
        self.run_column_onupdates()
        self.add_values_to_saver(update)
        update.execute(cursor)
        self.rowid = self.primary_key_values()

    def add_values_to_saver(self, saver):
        for column in self.table.concrete_columns():
            data = column.convert_for_db(getattr(self, column.name))
            saver.add_value(column.fullname(), data)
            # if the conversion changed the data, reflect that in our
            # attributes.
            setattr(self, column.name, data)

    def delete(self, cursor):
        delete = sql.Delete(self.table)
        delete.wheres.append(self.rowid_where())
        delete.execute(cursor)

    @classmethod
    def query(cls, *filter_args, **filter_kwargs):
        retval = query.Query(cls.table)
        retval.filter(*filter_args, **filter_kwargs)
        return retval

    @classmethod
    def get(cls, cursor, id, load=None, join=None):
        retval = query.Query(cls.table)
        for col, value in zip(cls.table.primary_keys, ensure_list(id)):
            retval.filter(col==value)
        if load is not None:
            retval.load(*ensure_list(load))
        if join is not None:
            retval.join(*ensure_list(join))
        try:
            return retval.get(cursor)
        except NotFoundError:
            raise NotFoundError("Record with id %s not found" % id)
        except TooManyResultsError:
            raise TooManyResultsError("Too many records with id %s" % id)

    def primary_key_values(self):
        return tuple(getattr(self, c.name) for c in self.table.primary_keys)

    def rowid_where(self):
        wheres = []
        for column, value in izip(self.table.primary_keys, self.rowid):
            wheres.append(column==value)
        return clause.Where.and_together(wheres)

    def join(self, *relation_names):
        me_list = query.ResultSet(self.__class__.table, [self])
        return me_list.join(*relation_names)
