from django.conf import settings

from channelguide import util
from channelguide.guide import forms
from channelguide.guide.auth import login_required

SESSION_KEY = 'submitted-feed'

def destroy_submit_url_session(request):
    if SESSION_KEY in request.session:
        del request.session[SESSION_KEY]

@login_required
def submit_feed(request):
    destroy_submit_url_session(request)
    if request.method != 'POST':
        form = forms.FeedURLForm(request.connection)
    else:
        form = forms.FeedURLForm(request.connection, request.POST.copy())
        if form.is_valid():
            request.session[SESSION_KEY] = form.get_feed_data()
            return util.redirect("channels/submit/step2")
    return util.render_to_response(request, 'submit-feed-url.html', 
            {'form': form})

@login_required
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

    if not SESSION_KEY in request.session:
        return util.redirect('channels/submit/step1')
    session_dict = request.session[SESSION_KEY]
    if request.method != 'POST':
        form = forms.SubmitChannelForm(request.connection)
        form.set_defaults(session_dict)
        session_dict['detected_thumbnail'] = form.set_image_from_feed
        request.session.modified = True
    else:
        form = forms.SubmitChannelForm(request.connection, 
                util.copy_post_and_files(request))
        if form.user_uploaded_file():
            session_dict['detected_thumbnail'] = False
            request.session.modified = True
        if form.is_valid():
            feed_url = request.session[SESSION_KEY]['url']
            form.save_channel(request.user, feed_url)
            destroy_submit_url_session(request)
            return util.redirect(settings.BASE_URL_FULL + "channels/submit/after?%s" % feed_url)
        else:
            form.save_submitted_thumbnail()
    context = form.get_template_data()
    if session_dict.get('detected_thumbnail'):
        context['thumbnail_description'] = _("Current image (from the feed)")
    else:
        context['thumbnail_description'] = _("Current image (uploaded)")
    return util.render_to_response(request, 'submit-channel.html', context)

def after_submit(request):
    url = request.META.get('QUERY_STRING')
    subscribe = util.get_subscription_url(url)
    def link(inside):
        return "<a href='%s' title='Miro: Internet TV'>%s</a>" % (subscribe, inside)
    textLink = '%s' % link("Your 1-Click Subscribe URL")
    buttons = [
        'http://subscribe.getmiro.com/img/buttons/one-click-subscribe-88X34.png',
        'http://subscribe.getmiro.com/img/buttons/one-click-subscribe-109X34.png']
    html = ['<ul><form name="buttoncode">']
    for button in buttons:
        img = "<img src='%s' alt='Miro Video Player' border='0' id='one-click-image' />" % button
        buttonLink = link(img)
        inputName = "btn%i" % len(html)
        wholeButton = '<li>%s<li><span>html:</span><input size="40" id="one-click-link" name="%s" value="%s" onClick="document.buttoncode.%s.select();">' % (img, inputName, buttonLink, inputName)
        html.append(wholeButton)
    html.append('</form>')
    html.append('<li><h3>' + textLink + '</h3>')
    html.append('</ul>')
    context = {
            'html' : ''.join(html),
            'url': url,
            }
    return util.render_to_response(request, 'after-submit.html', context)
