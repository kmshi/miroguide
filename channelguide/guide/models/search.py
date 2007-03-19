from channelguide.db import DBObject, dbutil
from sqlalchemy import select, text, desc, join, func

def score_column(class_, terms):
    query = ' '.join(terms)
    return (dbutil.match([class_.c.important_text], query) * 5 + 
        dbutil.match([class_.c.important_text, class_.c.text], query))

def where_clause(class_, terms):
    query = ' '.join(['+%s*' % t for t in terms])
    return dbutil.match([class_.c.important_text, class_.c.text], query,
            boolean=True)

class ChannelSearchData(DBObject):
    pass

class ItemSearchData(DBObject):
    pass
