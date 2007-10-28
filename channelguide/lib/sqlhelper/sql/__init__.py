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

"""sqlhelper.sql -- Build SQL statements programically.

This package can be used in a stand-alone manner, although it doesn't have a
ton of functionality.  Really it only has enough for the orm package to work.
But it should be pretty easy to extend.  If you do, please consider submitting
a patch.

This package defines 2 types of classes:
    * Statement objects represent a SQL statement (INSERT, DELETE, SELECT, 
      etc).  
    * Clause objects are the building blocks used to create statements.
"""
from statement import Select, Insert, Delete, Update
from expression import (Expression, Literal, Quoted, OrderBy, Join, CrossJoin,
        SimpleExpression, CompoundExpression, join, or_together, and_together,
        sum, product, RAND, NOW, COUNT, NULL)

def desc(text, *args):
    return OrderBy(Clause(text, *args), desc=True)
