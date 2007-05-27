"""sql package -- Build SQL statements programically.

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
