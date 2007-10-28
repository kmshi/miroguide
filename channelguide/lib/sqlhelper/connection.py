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

import time
class Connection(object):
    """Connection object.  This simplfies the python DB API's
    connection/cursor objects.  It has the following differences:

      * It stores both a connection and a cursor to that connection, so you
        can call execute(), commit() and rollback() on it.
      * execute() returns all the results immediately, no need for fetchall()
    """
    def __init__(self, raw_connection, logging=False):
        self.raw_connection = raw_connection
        self.cursor = raw_connection.cursor()
        if logging is not False:
            self.logfile = file(logging, 'a')
        else:
            self.logfile = None

    def execute(self, sql, args=None):
        s = time.time()
        self.cursor.execute(sql, args)
        t = time.time()
        rows = self.cursor.fetchall()
        v = time.time()
        if self.logfile is not None and not sql.startswith('SELECT'):
            self.logfile.write("""executing %r
with args: %r
execute took %f seconds
fetchall took %f seconds
""" % (sql, args, (t-s), (v-t)))
        return rows

    def commit(self):
        self.raw_connection.commit()

    def rollback(self):
        self.raw_connection.rollback()

    def close(self):
        self.cursor.close()
        self.raw_connection.close()
        if self.logfile is not None:
            self.logfile.close()

    def get_lastrowid(self):
        return self.cursor.lastrowid
    lastrowid = property(get_lastrowid)
