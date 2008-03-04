from channelguide.guide.models import Category, Channel, Language, Tag
from channelguide.guide import search as search_mod

def get_channel(connection, id):
    return Channel.get(connection, id, join=['categories', 'tags', 'items',
        'owner', 'language', 'secondary_languages'])

def get_channels(connection, filter, value):
    query = Channel.query_approved()
    if filter == 'category':
        try:
            category_id = Category.query(name=value).get(connection).id
        except LookupError:
            return []
        query.join('categories')
        query.joins['categories'].where(id=category_id)
    elif filter == 'tag':
        try:
            tag_id = Tag.query(name=value).get(connection).id
        except LookupError:
            return []
        query.join('tags')
        query.joins['tags'].where(id=tag_id)
    elif filter == 'language':
        try:
            language_id = Language.query(name=value).get(connection).id
        except LookupError:
            return []
        query.where((Channel.c.primary_language_id == language_id) |
                Language.secondary_language_exists_where(language_id))
    else:
        return []
    return query.execute(connection)

def search(connection, terms):
    query = search_mod.search_channels(terms)
    return query.execute(connection)
