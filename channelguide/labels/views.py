# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.contrib.auth.views import redirect_to_login
from django.core.paginator import Paginator, InvalidPage
from django.db.models import Count
from django.http import HttpResponseRedirect, Http404
from django.utils.translation import gettext as _
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.template.context import RequestContext

from channelguide.channels.models import Channel

def requires_model(func):
    def decorator(request, *args, **kwargs):
        if 'model' not in kwargs:
            raise ValueError('must pass a model attribute to %s' % func)
        return func(request, *args, **kwargs)
    return decorator

@requires_model
def index(request, model=None, group_name='Labeled Shows',
         template='labels/group-list.html', paginator_count=None):
    audio = request.path.startswith('/audio')
    if audio:
        labels = model.objects.filter(channels__state=Channel.AUDIO)
    else:
        labels = model.objects.filter(channels__state=Channel.APPROVED)
    labels = labels.annotate(channel_count=Count('channels'))
    if paginator_count is not None:
        paginator = Paginator(labels, paginator_count)
        try:
            page = paginator.page(request.GET.get('page', 1))
        except InvalidPage:
            raise Http404
    else:
        page = None
    return render_to_response(template, {
        'group_name': _(group_name),
        'groups': labels,
        'page': page,
        'audio': audio
    }, context_instance=RequestContext(request))

@requires_model
def moderate(request, model=None, header='Edit Label', new_label='New Label',
             template='labels/edit-labels.html'):
    name = model._meta.object_name.lower()
    for perm in 'add', 'change', 'delete':
        if request.user.has_perm('labels.%s_%s' % (perm, name)):
            break
    else:
        return redirect_to_login(request.path)

    return render_to_response(template, {
        'header': _(header),
        'new_label': _(new_label),
        'labels': model.objects.all(),
        'add_perm': request.user.has_perm('labels.add_%s' % name),
        'add_url': reverse('%s-add' % name),
        'change_perm': request.user.has_perm('labels.change_%s' % name),
        'change_url': reverse('%s-change' % name),
        'delete_perm': request.user.has_perm('labels.delete_%s' % name),
        'delete_url': reverse('%s-delete' % name),
    }, context_instance=RequestContext(request))

@requires_model
def add(request, model=None):
    if not request.user.has_perm('labels.add_%s' %
                                 model._meta.object_name.lower()):
        return redirect_to_login(request.path)
    if request.method == 'POST':
        model.objects.create(name=request.POST['name'])
    return HttpResponseRedirect(reverse('%s-moderate' %
                                        model._meta.object_name.lower()))

@requires_model
def delete(request, model=None):
    if not request.user.has_perm('labels.delete_%s' %
                                 model._meta.object_name.lower()):
        return redirect_to_login(request.path)
    if request.method == 'POST':
        model.objects.get(pk=request.POST['id']).delete()
    return HttpResponseRedirect(reverse('%s-moderate' %
                                        model._meta.object_name.lower()))

@requires_model
def change_name(request, model=None):
    if not request.user.has_perm('labels.change_%s' %
                                 model._meta.object_name.lower()):
        return redirect_to_login(request.path)
    if request.method == 'POST' and request.POST.get('name'):
        label = model.objects.get(pk=request.POST['id'])
        label.name = request.POST['name']
        label.save()
    return HttpResponseRedirect(reverse('%s-moderate' %
                                        model._meta.object_name.lower()))


