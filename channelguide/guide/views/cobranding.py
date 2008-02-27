# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django.http import Http404
from channelguide import util
from channelguide.guide import templateutil, auth
from channelguide.guide.models import Channel, Cobranding, User
from channelguide.guide.forms import CobrandingAdminForm

@auth.login_required
def admin(request, cobrand_name):
    if Cobranding.query(Cobranding.c.name==cobrand_name).count(request.connection) == 0: # doesn't exist
        if not request.user.is_admin():
            raise Http404
        c = Cobranding()
        c.name = c.html_title = c.page_title = c.url = c.description = cobrand_name
        try:
            c.save(request.connection)
        except:
            raise Http404
    if not (request.user.is_admin() or cobrand_name == request.user.username):
        return util.send_to_login_page(request)
    cobrand = Cobranding.get(request.connection, cobrand_name)
    if request.method != 'POST':
        form = CobrandingAdminForm(request.connection, cobrand)
    else:
        form = CobrandingAdminForm(request.connection, cobrand,
                request.POST.copy())
        if form.is_valid():
            form.update_cobrand()
    return util.render_to_response(request, 'cobranding-admin.html',
            {'cobrand': cobrand, 'form': form})

def cobranding(request, cobrand_name):
    try:
        cobrand = Cobranding.get(request.connection, cobrand_name)
    except:
        raise Http404
    user = User.query(User.c.username==cobrand_name).join('channels').execute(request.connection)[0]
    query = Channel.query().where(Channel.c.owner_id==user.id)
    query.where(Channel.c.state.in_((Channel.APPROVED, Channel.AUDIO)))
    query.order_by(Channel.c.hi_def, desc=True)
    query.order_by(Channel.c.name)
    pager = templateutil.Pager(6, query, request)
    return util.render_to_response(request, 'cobranding.html', {
        'cobrand': cobrand,
        'pager': pager
        })
