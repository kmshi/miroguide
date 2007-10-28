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

"""sqlhelper.  SQL query builder and object-relational mapping package.

SQLHelper has tools to help with the following tasks:

sqlhelper.sql: Build SQL Expressions.
sqlhelper.orm: Object-Relational mapping.
sqlhelper.dbupdate: Manage updating a database schema.
sqlhelper.pool: Connection pooling
"""

import logging
logging.addLevelName(5, "SQL")
logging.sql = lambda msg, *args, **kargs: logging.log(5, msg, *args, **kargs)
logging.SQL = 5

from exceptions import SQLError, NotFoundError, TooManyResultsError
from sqlhelper.sql import *
from sqlhelper.orm import *
