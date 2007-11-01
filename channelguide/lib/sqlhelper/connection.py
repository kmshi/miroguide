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
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

class Connection(object):
    """Connection object.  This simplfies the python DB API's
    connection/cursor objects.  It has the following differences:

      * It stores both a connection and a cursor to that connection, so you
        can call execute(), commit() and rollback() on it.
      * execute() returns all the results immediately, no need for fetchall()
    """
    def __init__(self, dbinfo, use_connection=None):
        """Create a new connection """
        self.dbinfo = dbinfo
        if use_connection is None:
            self.raw_connection = dbinfo.connect()
        else:
            self.raw_connection = use_connection
        self.cursor = self.raw_connection.cursor()

    def execute(self, sql, args=None):
        self.cursor.execute(sql, args)
        if self.cursor.description is not None:
            return self.cursor.fetchall()
        else:
            return None

    def commit(self):
        self.raw_connection.commit()

    def rollback(self):
        self.raw_connection.rollback()

    def close(self):
        self.cursor.close()
        self.raw_connection.close()

    def get_autoincrement_value(self, table, column):
        return self.dbinfo.get_autoincrement_value(self.cursor, table, column)

    def is_open(self):
        return self.dbinfo.is_connection_open(self.raw_connection)
