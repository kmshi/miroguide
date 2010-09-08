# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

"""search channels."""
from channelguide import util
from channelguide.channels.models import Channel

def search_score(terms):
    query = ' '.join(terms)
    important = '(MATCH(cg_channel_search_data.important_text) AGAINST(%s))'
    normal = ('MATCH(cg_channel_search_data.important_text,'
              'cg_channel_search_data.text) AGAINST(%s)')
    return '(%s) * 50 + %s' % (important, normal), [query, query]

def search_where(terms):
    query = ' '.join(u'+%s*' % t for t in terms)
    return ('MATCH(cg_channel_search_data.important_text,'
            'cg_channel_search_data.text) AGAINST(%s IN BOOLEAN MODE)',
            [query])

def contains_hd(terms):
    return 'hd' in [term.lower() for term in terms]

def search_channels(query, terms):
    terms = util.ensure_list(terms)
    if contains_hd(terms):
        query = query.filter(hi_def=True)
        terms = [t for t in terms if t.lower() != 'hd']
    terms = [t for t in terms if len(t) >= 3] # strip short terms
    sql, args = search_score(terms)

    query = query.extra(select = {'search_score': sql},
                        select_params = args)

    sql, args = search_where(terms)
    query = query.filter(search_data__text__isnull=False) # hack to join the
                                                          # search table
    query = query.extra(where = [sql],
                        params = args)
    query = query.order_by().order_by('archived')
    query = query.extra(order_by=['-search_score'])
    return query

def search_feeds(terms):
    query = search_channels(terms)
    return query.where(Channel.c.url.is_not(None))

def search_shows(terms):
    query = search_channels(terms)
    return query.where(Channel.c.url.is_(None))
