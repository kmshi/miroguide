from django.http import HttpResponse

from channelguide import util
from channelguide.guide import forms
from channelguide.guide.auth import login_required
from channelguide.guide.models import Channel, ChannelNote

from datetime import datetime

SESSION_KEY = 'submitted-feed'

def destroy_submit_url_session(request):
    if SESSION_KEY in request.session:
        del request.session[SESSION_KEY]

@login_required
def submit_feed(request):
    destroy_submit_url_session(request)
    if request.method != 'POST':
        form = forms.FeedURLForm(
            request.connection, url_required=(not request.user.is_moderator()))
    else:
        submit_type = request.POST.get('type', '')
        form = forms.FeedURLForm(
            request.connection, request.POST.copy(),
            url_required=(not request.user.is_moderator()))
        if form.is_valid():
            if form.cleaned_data['url']:
                request.session[SESSION_KEY] = form.get_feed_data()
            else:
                request.session[SESSION_KEY] = form.cleaned_data
            if 'Fan' in submit_type:
                request.session[SESSION_KEY]['owner-is-fan'] = True
            else:
                request.session[SESSION_KEY]['owner-is-fan'] = False
                if request.session[SESSION_KEY].get('publisher') is None:
                    request.session[SESSION_KEY]['publisher'] = \
                                                              request.user.email
            return util.redirect("submit/step2")
        else:
            for error in form.error_list():
                if (unicode(error['name']) == 'RSS Feed' and
                    'is already a channel in the guide' in
                    unicode(error['message'])):
                    url = form.data['url'].strip()
                    try:
                        channel = Channel.query(url=url).get(request.connection)
                    except LookupError:
                        raise # not sure what to do here
                    request.session[SESSION_KEY] = {'url': url}
                    return util.render_to_response(request,
                                                   'submit-feed-exists.html',
                                                   {'channel': channel})
    return util.render_to_response(request, 'submit-feed-url.html',
            {'form': form})

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
    if 'subscribe' in session_dict:
        return util.redirect('/submit')
    if request.method != 'POST':
        form = forms.SubmitChannelForm(request.connection)
        form.set_defaults(session_dict)
        session_dict['detected_thumbnail'] = form.set_image_from_feed
        request.session.modified = True
    else:
        form = forms.SubmitChannelForm(request.connection,
                util.copy_post_and_files(request))
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
            return HttpResponse('SUBMIT SUCCESS')
        else:
            form.save_submitted_thumbnail()
    context = form.get_template_data()
    if session_dict.get('detected_thumbnail'):
        context['thumbnail_description'] = _("Current image (from the feed)")
    else:
        context['thumbnail_description'] = _("Current image (uploaded)")
    return util.render_to_response(request, 'submit-channel.html', context)

@login_required
@check_session_key
def after_submit(request):
    subscribe = request.session[SESSION_KEY].get('subscribe')
    if not subscribe:
        return util.redirect('submit')
    def img(url):
        return "<img src='%s' alt='Miro Video Player' border='0' class='one-click-image' />" % url
    def link(inside):
        return "<a href='%s' title='Miro: Internet TV'>%s</a>" % (subscribe, inside)
    textLink = '%s' % link("Your 1-Click Subscribe URL")
    buttons = [
        'http://subscribe.getmiro.com/img/buttons/one-click-subscribe-88X34.png',
        'http://subscribe.getmiro.com/img/buttons/one-click-subscribe-109X34.png']
    buttonHTML = [link(img(url)) for url in buttons]
    context = {
        'buttons': buttonHTML,
        'subscribe': subscribe,
        }
    return util.render_to_response(request, 'after-submit.html', context)

@login_required
@check_session_key
def claim(request):
    if request.method != 'POST':
        return util.redirect('submit')
    url = request.session[SESSION_KEY]['url']
    channel = Channel.query(url=url).get(request.connection)
    note = ChannelNote(request.user,
                       'This user (%s) has asked to claim this channel.' % (
        request.user.username))
    channel.add_note(request.connection, note)
    channel.waiting_for_reply_date = datetime.now()
    channel.save(request.connection)
    return util.render_to_response(request, 'submit-feed-claim.html',
                                   {'channel': channel})
