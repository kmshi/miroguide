from exceptions import SQLError, NotFoundError, TooManyResultsError
from sql.clause import Clause, NOW, COUNT, RAND

def escape(text, *args):
    return Clause(text, args)
