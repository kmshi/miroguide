class NotFoundError(LookupError):
    """An object was not found in the database."""
    pass

class TooManyResultsError(Exception):
    """Multiple records were returned when we expected one."""
    pass
