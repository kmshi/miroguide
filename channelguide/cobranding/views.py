# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.http import Http404
from django.core.paginator import Paginator, InvalidPage
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from channelguide.channels.models import Channel
from channelguide.cobranding.models import Cobranding
from channelguide.cobranding.forms import CobrandingAdminForm

@login_required
def admin(request, cobrand_name):
    if not (request.user.is_superuser or
            cobrand_name == request.user.username):
        return redirect_to_login(request.path)
    try:
        cobrand = Cobranding.objects.get(user=cobrand_name)
    except Cobranding.DoesNotExist:
        if not request.user.is_superuser:
            raise Http404
        user = User.objects.get(username=cobrand_name)
        cobrand = Cobranding(user=user,
                             html_title=cobrand_name,
                             page_title=cobrand_name,
                             url=cobrand_name,
                             description=cobrand_name)
        try:
            cobrand.save()
        except:
            raise Http404
    if request.method != 'POST':
        form = CobrandingAdminForm(cobrand)
    else:
        form = CobrandingAdminForm(cobrand,
                                   request.POST.copy())
        if form.is_valid():
            form.update_cobrand()
    return render_to_response('cobranding/cobranding-admin.html',
                              {'cobrand': cobrand,
                               'form': form},
                              context_instance=RequestContext(request))

def cobranding(request, cobrand_name):
    try:
        cobrand = Cobranding.objects.get(user=cobrand_name)
    except Cobranding.DoesNotExist:
        raise Http404
    channels = Channel.objects.approved().filter(owner=cobrand.user).order_by(
        'archived', '-hi_def', 'state', 'name')
    paginator = Paginator(channels, 6)
    try:
        page = paginator.page(request.GET.get('page', 1))
    except InvalidPage:
        raise Http404
    return render_to_response('cobranding/cobranding.html', {
            'cobrand': cobrand,
            'page': page
            }, context_instance=RequestContext(request))
