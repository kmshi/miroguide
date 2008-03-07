from channelguide.guide.models import Category, Channel, Language, Tag
from channelguide.guide import search as search_mod

def get_channel(connection, id):
    return Channel.get(connection, id, join=['categories', 'tags', 'items',
        'owner', 'language', 'secondary_languages'])

def get_channels(connection, filter, value, sort=None, limit=None, offset=None):
    query = Channel.query_approved()
    join = None
    if filter == 'category':
        try:
            category_id = Category.query(name=value).get(connection).id
        except LookupError:
            return []
        join = 'categories'
        query.join(join)
        query.joins[join].where(id=category_id)
    elif filter == 'tag':
        try:
            tag_id = Tag.query(name=value).get(connection).id
        except LookupError:
            return []
        join = 'tags'
        query.join(join)
        query.joins[join].where(id=tag_id)
    elif filter == 'language':
        try:
            language_id = Language.query(name=value).get(connection).id
        except LookupError:
            return []
        query.where((Channel.c.primary_language_id == language_id) |
                Language.secondary_language_exists_where(language_id))
    elif filter == 'name':
        if value:
            query.where(Channel.c.name.like(value + '%'))
    else:
        return []
    if sort is not None and sort[0] == '-':
        desc = True
        sort = sort[1:]
    else:
        desc = False
    if sort in ('name', 'id'):
        query.order_by(sort, desc=desc)
    elif sort == 'age':
        query.order_by('approved_at', desc=desc)
    elif sort == 'popular':
        query.load('subscription_count_month')
        query.order_by('subscription_count_month', desc=desc)
    elif sort == 'rating':
        query.join('rating')
        query.order_by(query.joins['rating'].c.average, desc=desc)
    else: # default to name
        query.order_by('name')
    if limit is None:
        limit = 20
    if limit > 100:
        limit = 100
    if offset is None:
        offset = 0
    query.limit(limit).offset(offset)
    results = query.execute(connection)
    if join:
        for result in results:
            delattr(result, join)
    return results

def search(connection, terms):
    query = search_mod.search_channels(terms)
    return query.execute(connection)
