"""object-relational mapping package.

My (ben) plan is to keep this package fairly self-contained and to not have it
reference django, or the rest of the channel guide.  I think it should be
really easy to use it in different projects.  The one exception currently is
test cases, it's just so nice to use channel guide's test framework.
"""

import logging
logging.addLevelName(5, "SQL")
logging.sql = lambda msg, *args, **kargs: logging.log(5, msg, *args, **kargs)
logging.SQL = 5

from exceptions import NotFoundError, TooManyResultsError
from table import Table
from record import Record
