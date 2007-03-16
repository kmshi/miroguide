from channelguide import util
from channelguide.guide.auth import moderator_required
from channelguide.guide.models import Language, Channel
from channelguide.guide.templateutil import make_two_column_list

def index(request):
    q = request.db_session.query(Language)
    return util.render_to_response(request, 'group-list.html', {
        'group_name': _('Channels by Language'),
        'groups': q.select(order_by=Language.c.name),
    })

def view(request, id):
    q = request.db_session.query(Channel)
    join_clause = q.join_to('language') | q.join_to('secondary_languages')
    return make_two_column_list(request, id, Language, _('Language: %s'),
            join_clause=join_clause)

@moderator_required
def moderate(request):
    query = request.db_session.query(Language, order_by='name')
    return util.render_to_response(request, 'edit-languages.html', {
        'languages': query.select().list(),
    })

@moderator_required
def add(request):
    if request.method == 'POST':
        new_lang = Language(request.POST['name'])
        request.db_session.save(new_lang)
    return util.redirect('languages/moderate')

@moderator_required
def delete(request):
    if request.method == 'POST':
        lang = request.db_session.get(Language, request.POST['id'])
        request.db_session.delete(lang)
    return util.redirect('languages/moderate')

@moderator_required
def change_name(request):
    if request.method == 'POST':
        lang = request.db_session.get(Language, request.POST['id'])
        lang.name = request.POST['name']
        request.db_session.update(lang)
    return util.redirect('languages/moderate')
