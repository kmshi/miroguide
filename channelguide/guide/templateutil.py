# Copyright (c) 2008-9 Participatory Culture Foundation
# See LICENSE for details.

"""Helper classes for the templates"""

class QueryObjectList:
    def __init__(self, connection, query):
        self.connection = connection
        self.query = query

    def __len__(self):
        return int(self.query.count(self.connection))

    def __getslice__(self, offset, end):
        limit = end - offset
        return self.query.limit(limit).offset(offset).execute(self.connection)
