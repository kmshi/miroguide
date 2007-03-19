class AuthError(Exception):
    pass

class FeedparserEntryError(ValueError):
    """Error parsing a feedparser entry object"""
    pass

class EntryMissingDataError(ValueError):
    """A feedparser entry doesn't have the data we need"""
    pass
