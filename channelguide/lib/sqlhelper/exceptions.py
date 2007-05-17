class SQLError(Exception):
    """Error executing SQL."""
    pass

class NotFoundError(LookupError):
    """An row was not found in the database."""
    pass

class TooManyResultsError(Exception):
    """Multiple rows were returned when we expected one."""
    pass
