"""sql package -- Build SQL statements programically.

This package defines 2 types of classes:
    * Statement objects represent a SQL statement (INSERT, DELETE, SELECT, 
      etc).  
    * Clause objects are the building blocks used to create statements.
"""
from exceptions import SQLError
from statement import Select, Insert, Delete, Update
