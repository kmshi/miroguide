class AuthError(Exception):
    pass

class FeedparserEntryError(ValueError):
    """Error parsing a feedparser entry object"""
    pass
