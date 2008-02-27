# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

class AuthError(Exception):
    pass

class FeedparserEntryError(ValueError):
    """Error parsing a feedparser entry object"""
    pass

class EntryMissingDataError(ValueError):
    """A feedparser entry doesn't have the data we need"""
    pass
