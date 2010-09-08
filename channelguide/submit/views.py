# Copyright (c) 2009 Participatory Culture Foundation
# See LICENSE for details.

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.translation import ugettext as _

from channelguide import util
from channelguide.channels.forms import FeedURLForm, SubmitChannelForm
from channelguide.channels.models import Channel
from channelguide.notes.models import ChannelNote

SESSION_KEY = 'submitted-feed'

def destroy_submit_url_session(request):
    if SESSION_KEY in request.session:
        del request.session[SESSION_KEY]

@login_required
def submit_feed(request):
    destroy_submit_url_session(request)
    url_required = not request.user.has_perm('channels.add_site')
    if request.method != 'POST':
        form = FeedURLForm(url_required=url_required)
        form.fields['url'].initial = request.GET.get('url', '')
        form.fields['name'].initial = request.GET.get('name', '')
    else:
        submit_type = request.POST.get('type', '')
        form = FeedURLForm(request.POST.copy(),
            url_required=url_required)
        if form.is_valid():
            if form.cleaned_data['url']:
                request.session[SESSION_KEY] = form.get_feed_data()
            else:
                request.session[SESSION_KEY] = form.cleaned_data
            if 'Fan' in submit_type:
                request.session[SESSION_KEY]['owner-is-fan'] = True
            else:
                request.session[SESSION_KEY]['owner-is-fan'] = False
            return util.redirect("submit/step2")
        else:
            if 'url' in form.data:
                try:
                    channel = Channel.objects.get(url=form.data['url'])
                except Channel.DoesNotExist:
                    pass
                else:
                    request.session[SESSION_KEY] = {'url': channel.url}
                    return render_to_response(
                        'submit/submit-feed-exists.html',
                        {'channel': channel},
                        context_instance=RequestContext(request))
    return render_to_response('submit/submit-feed-url.html',
                              {'form': form},
                              context_instance=RequestContext(request))

def check_session_key(function):
    def check(request, *args, **kw):
        if SESSION_KEY not in request.session:
            return util.redirect('submit')
        return function(request, *args, **kw)
    return check

@login_required
@check_session_key
def submit_channel(request):
    """
    Called when the user is submitting a channel.  If the SESSION_KEY
    cookie isn't set, then we redirect back to the first step.
    XXX: check for clients that don't support cookies

    If the submisstion used the GET method, we create a form that allows
    the submitter to describe the feed in more detail (languages, categories,
    tags, etc.).

    If the submission used the POST method, we check to see if the submitted
    form is valid; if it is we create the channel and redirect to the
    post-submission page.  Otherwise, redisplay the form with the errors
    highlighted.
    """
    session_dict = request.session[SESSION_KEY]
    url_required = not request.user.has_perm('channels.add_site')
    if 'subscribe' in session_dict:
        return util.redirect('/submit/')
    if request.method != 'POST':
        form = SubmitChannelForm(url_required=url_required)
        form.set_defaults(session_dict)
        session_dict['detected_thumbnail'] = form.set_image_from_feed
        request.session.modified = True
    else:
        form = SubmitChannelForm(request.POST, request.FILES,
                                 url_required=url_required)
        if session_dict['owner-is-fan']:
            form.fields['publisher'].required = False
        if form.user_uploaded_file():
            session_dict['detected_thumbnail'] = False
            request.session.modified = True
        if form.is_valid():
            feed_url = session_dict['url']
            channel = form.save_channel(request.user, feed_url)
            session_dict['subscribe'] = channel.get_subscription_url()
            request.session.modified = True
            if request.FILES.get('thumbnail_file'):
                request.FILES['thumbnail_file'].close()
            return util.redirect('submit/after')
        else:
            form.save_submitted_thumbnail()
    context = form.get_template_data()
    if session_dict.get('detected_thumbnail'):
        context['thumbnail_description'] = _("Current image (from the feed)")
    else:
        context['thumbnail_description'] = _("Current image (uploaded)")
    response = render_to_response('submit/submit-channel.html', context,
                                  context_instance=RequestContext(request))
    if request.FILES.get('thumbnail_file'):
        request.FILES['thumbnail_file'].close()
    return response

@login_required
@check_session_key
def after_submit(request):
    subscribe = request.session[SESSION_KEY].get('subscribe')
    if not subscribe:
        return util.redirect('submit')
    def img(url):
        return ("<img src='%s' alt='Miro Video Player' border='0' "
                "class='one-click-image' />" % url)
    def link(inside):
        return "<a href='%s' title='Miro: Internet TV'>%s</a>" % (subscribe,
                                                                  inside)
    textLink = '%s' % link("Your 1-Click Subscribe URL")
    button_prefix = 'http://subscribe.getmiro.com/img/buttons/'
    buttons = [
        'one-click-subscribe-88X34.png',
        'one-click-subscribe-109X34.png']
    buttonHTML = [link(img(button_prefix + url)) for url in buttons]
    context = {
        'buttons': buttonHTML,
        'subscribe': subscribe,
        'textlink': textLink
        }
    return render_to_response('submit/after-submit.html', context,
                              context_instance=RequestContext(request))

@login_required
@check_session_key
def claim(request):
    if request.method != 'POST':
        return util.redirect('submit')
    url = request.session[SESSION_KEY]['url']
    channel = Channel.objects.get(url=url)
    ChannelNote.objects.create(channel=channel,
                               user=request.user,
                               title='',
                               body=(
            'This user (%s) has asked to claim this channel.' % (
                request.user.username)))
    return render_to_response('submit/submit-feed-claim.html',
                              {'channel': channel},
                              context_instance=RequestContext(request))
