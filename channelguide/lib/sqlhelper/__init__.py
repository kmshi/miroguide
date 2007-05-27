"""sqlhelper.  SQL query builder and object-relational mapping package.

My (ben) plan is to keep this package fairly self-contained and to not have it
reference django, or the rest of the channel guide.  I think it should be
pretty easy to use it in different projects.  
"""

import logging
logging.addLevelName(5, "SQL")
logging.sql = lambda msg, *args, **kargs: logging.log(5, msg, *args, **kargs)
logging.SQL = 5

from exceptions import SQLError, NotFoundError, TooManyResultsError
from sqlhelper.sql import *
from sqlhelper.orm import *
