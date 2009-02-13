
# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

"""Util package.  Used for often used convenience functions. """

from datetime import datetime, timedelta
from itertools import cycle, count, izip
from urllib import quote, quote_plus, urlopen, unquote_plus
from xml.sax import saxutils
import Queue
import cgi
import logging
import md5
import os
import re
import random
import simplejson
import string
import subprocess
import sys
import textwrap
import threading
import socket # for socket.error

from django.template import loader
from django.template.context import RequestContext
from django.core.mail import send_mail as django_send_mail
from django.conf import settings
from django.utils.http import urlquote
from django.utils.translation import ugettext as _
from django.http import HttpResponse, HttpResponseRedirect, Http404
try:
    from django.utils.safestring import mark_safe
    mark_safe = mark_safe # fix pyflakes error
except ImportError:
    mark_safe = lambda x: x
emailer = None


# sharing urls
DELICIOUS_URL = "http://del.icio.us/post?v=4&noui&jump=close&url=%s&title=%s"
DIGG_URL = "http://digg.com/submit/?url=%s&media=video"
REDDIT_URL = "http://reddit.com/submit?url=%s&title=%s"
STUMBLEUPON_URL = "http://www.stumbleupon.com/submit?url=%s&title=%s"
FACEBOOK_URL = "http://www.facebook.com/share.php?u=%s"
TWITTER_URL = "http://www.twitter.com/home?status=%s"

# common regexps
MIRO_VERSION_RE = re.compile('^.*Miro\/(?P<miro_version>(?:\d+\.)*\d).*$')


def get_miro_version(http_user_agent):
    if not http_user_agent:
        return None
    version_match = MIRO_VERSION_RE.match(http_user_agent)
    if version_match:
        return version_match.group('miro_version')
    else:
        return None

def bitly_shorten(url):
    if not settings.BITLY_USERNAME or not settings.BITLY_API_KEY:
        return url
    key = 'bitly_shorten:%s' % md5.new(url).hexdigest()
    json = urlopen('http://api.bit.ly/shorten?version=2.0.1&longUrl=%s&login=%s&apiKey=%s' % (
            quote(url), settings.BITLY_USERNAME, settings.BITLY_API_KEY)).read()
    parsed = simplejson.loads(json)
    url = parsed['results'][url]['shortUrl']
    return url

def get_share_links(url, name):
    share_delicious = DELICIOUS_URL % (quote(url),
                                       quote(name.encode('utf8')))
    share_digg = DIGG_URL % quote(url)
    share_reddit = REDDIT_URL % (quote(url), quote(name.encode('utf8')))
    share_stumbleupon = STUMBLEUPON_URL % (quote(url),
                                           quote(name.encode('utf8')))
    share_facebook = FACEBOOK_URL % (quote(url))
    share_twitter = TWITTER_URL % (_('Watching in Miro: %s') % bitly_shorten(url)).replace(' ', '+')

    ## Generate dictionary
    share_links = {
        'url': url,
        'delicious': share_delicious,
        'digg': share_digg,
        'reddit': share_reddit,
        'stumbleupon': share_stumbleupon,
        'facebook': share_facebook,
        'twitter': share_twitter}

    return share_links


def render_to_response(request, template_name, context=None, **kwargs):
    """channel guide version of render_to_response.  It passes the template a
    RequestContext object instead of the standard Context object.  
    """
    template_name = 'guide/' + template_name
    kwargs['context_instance'] = RequestContext(request)
    return HttpResponse(loader.render_to_string(template_name, context, **kwargs))

def import_last_component(name):
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

def make_absolute_url(relative_url, get_data=None):
    if relative_url.startswith('http://') or \
            relative_url.startswith('https://'):
        return relative_url + format_get_data(get_data)
    if (relative_url and relative_url[0] == '/' and
        settings.BASE_URL_FULL[-1] == '/'):
        relative_url = relative_url[1:]
    return settings.BASE_URL_FULL + relative_url + format_get_data(get_data)

def make_url(relative_url, get_data=None):
    if '?' in relative_url: # a query
        relative_url, query = relative_url.split('?', 1)
        get_data_list = [f.split('=', 1) for f in query.split('&')]
        get_data = dict((k, unquote_plus(v).decode('utf8')) for (k, v) in
                         get_data_list)
    return mark_safe(
            urlquote(settings.BASE_URL + relative_url) +
            format_get_data(get_data))

def format_get_data(get_data):
    if not get_data:
        return ''
    parts = []
    for key, value in get_data.items():
        if isinstance(value, (list, tuple)):
            for subvalue in value:
                parts.append('%s=%s' % (key, quote(subvalue.encode('utf8'))))
        else:
            parts.append('%s=%s' % (key, quote(value.encode('utf8'))))
    return '?' + '&'.join(parts)

def get_relative_path(request):
    path = request.get_full_path()
    if path.startswith(settings.BASE_URL_PATH):
        return path[len(settings.BASE_URL_PATH):]
    else:
        return path

def redirect(url, get_data=None):
    if url_is_relative(url):
        url = make_absolute_url(url)
    url += format_get_data(get_data)
    return HttpResponseRedirect(url)

def redirect_to_referrer(request):
    try:
        referrer = request.META['HTTP_REFERER']
        if '/accounts/login' in referrer:
            raise KeyError
        return redirect(referrer)
    except KeyError:
        return redirect(settings.BASE_URL)

def send_to_login_page(request):
    login_url = '/accounts/login?next=%s' % quote(get_relative_path(request))
    return redirect(login_url)

def make_qs(**query_dict):
    parts = []
    for key, value in query_dict:
        parts.append('%s=%s' % (quote(key, safe=''), quote(value, safe='')))
    return '?' + parts.join('&')

def read_file(path, mode='b'):
    f = open(path, 'r' + mode)
    try:
        return f.read()
    finally:
        f.close()

def write_file(path, data, mode='b'):
    f = open(path, 'w' + mode)
    try:
        f.write(data)
    finally:
        f.close()

def get_image_extension(image_data):
    try:
        identify_output = call_command('identify', '-', data=image_data)
    except EnvironmentError:
        raise ValueError('not an image we could identify')
    return identify_output.split(" ")[1].lower()

def push_media_to_s3(subpath, content_type):
    """
    Upload a subpath of the media directory to S3.
    """
    if not settings.USE_S3:
        return
    import S3
    conn = S3.AWSAuthConnection(settings.S3_ACCESS_KEY, settings.S3_SECRET_KEY)
    localPath = os.path.join(settings.MEDIA_ROOT, subpath)
    obj = S3.S3Object(file(localPath).read())
    count = 5
    while True:
        try:
            conn.put(settings.S3_BUCKET,
                     settings.S3_PATH + subpath,
                     obj,
                     {'Content-Type': content_type,
                      'x-amz-acl': 'public-read'})
        except:
            count -= 1
            if not count:
                raise
        else:
            return
        

def make_thumbnail(source_path, dest_path, width, height):
    # From the "Pad Out Image" recipe at
    # http://www.imagemagick.org/Usage/thumbnails/
    border_width = max(width, height) / 2
    try: 
        call_command("convert",  source_path, 
                     "-strip",
                     "-resize", "%dx%d>" % (width, height), 
                     "-gravity", "center", "-bordercolor", "black",
                     "-border", "%s" % border_width,
                     "-crop", "%dx%d+0+0" % (width, height),
                     "+repage", dest_path)
    except EnvironmentError:
        logging.exception('error resizing image')
        raise ValueError('could not resize image')

def copy_post_and_files(request):
    data = request.POST.copy()
    data.update(request.FILES)
    return data

def set_cookie(response, key, value, seconds):
    expires_at = datetime.now() + timedelta(seconds=seconds)
    if settings.USE_SECURE_COOKIES:
        secure=True
    else:
        secure=None
    response.set_cookie(key, value, max_age=seconds,
            expires=expires_at.strftime("%a, %d-%b-%Y %H:%M:%S GMT"),
            secure=secure)

def hash_string(str):
    return md5.new(str.encode('utf8')).hexdigest()

def get_object_or_404(connection, record_or_query, id):
    from sqlhelper.orm import Record
    if isinstance(record_or_query, Record):
        query = record_or_query.query()
    else:
        query = record_or_query
    try:
        return query.get(connection, id)
    except LookupError:
        raise Http404

def get_object_or_404_by_name(connection, record_or_query, name):
    if hasattr(record_or_query, 'query'):
        query = record_or_query.query()
    else:
        query = record_or_query
    query.where(query.c.name==name)
    ret = query.execute(connection)
    if len(ret) == 1:
        return ret[0]
    else:
        raise Http404

def send_mail(title, body, recipient_list, email_from=None, break_lines=True):
    global emailer
    if break_lines:
        body = '\n'.join(textwrap.fill(p) for p in body.split('\n'))
    if emailer is None:
        if not settings.EMAIL_FROM:
            return
        email_func = django_send_mail
    else:
        email_func = emailer
    if email_from is None:
        email_from = settings.EMAIL_FROM
    for email_to in ensure_list(recipient_list):
        try:
            email_func(title, body, email_from, [email_to])
        except socket.error:
            pass

class URLGrabber(threading.Thread):
    def __init__(self, in_queue, out_queue):
        threading.Thread.__init__(self)
        self.in_queue = in_queue
        self.out_queue = out_queue

    def run(self):
        while True:
            try:
                url = self.in_queue.get(block=False)
            except Queue.Empty:
                return
            try:
                data = urlopen(url).read()
            except Exception, e:
                self.out_queue.put((url, e))
            else:
                self.out_queue.put((url, data))

class ProgressPrinter:
    def __init__(self, prefix, total):
        self.prefix = prefix
        self.total = total
        throttle_interval = max(10, min(100, total / 1000))
        self.throttler = cycle(xrange(throttle_interval))
        self.count = 0

    def print_status(self):
        try:
            percent = self.count * 100.0 / self.total
        except ZeroDivisionError:
            percent = 100.0
        sys.stdout.write("\r%s (%d/%d) %.1f%%" % (self.prefix, self.count,
            self.total, percent))
        sys.stdout.flush()

    def iteration_done(self):
        self.count += 1
        if self.throttler.next() == 0:
            self.print_status()

    def loop_done(self):
        self.print_status()
        print

def grab_urls(urls, num_threads=5):
    """Download a list of urls quickly.  Uses multiple threads to parallelize
    the downloading.  Returns a list of (url, result) pairs.  result is either
    the page content, or an exception.
    """

    in_queue = Queue.Queue()
    out_queue = Queue.Queue()
    pprinter = ProgressPrinter("downloading", len(urls))
    for url in urls:
        in_queue.put(url)
    threads = [URLGrabber(in_queue, out_queue) for i in range(num_threads)]
    for t in threads:
        t.start()
    results = []
    while len(results) < len(urls):
        results.append(out_queue.get())
        pprinter.iteration_done()
    pprinter.loop_done()
    return results

subprocess_lock = threading.Lock()
def call_command(*args, **kwargs):
    data = kwargs.pop('data', None)
    if kwargs:
        raise TypeError('extra keyword args: %s' % kwargs.keys())
    subprocess_lock.acquire()
    try:
        pipe = subprocess.Popen(args, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if data is not None:
            pipe.stdin.write(data)
        pipe.stdin.close()
        stdout = pipe.stdout.read()
        stderr = pipe.stderr.read()
        returncode = pipe.wait()
    finally:
        subprocess_lock.release()
    if returncode != 0:
        raise OSError("Error running %r: %s\n(return code %s)" % 
                (args, stderr, returncode))
    else:
        return stdout

def url_is_relative(url):
    return '://' not in url and url != '#' and not url.startswith("/")

def make_link_attributes(href, css_class=None, **extra_link_attributes):
    if url_is_relative(href):
        href = make_url(href)
    href = saxutils.escape(href)
    attributes = []
    attributes.append('href="%s"' % mark_safe(href))
    if 'onclick' not in extra_link_attributes:
        attributes.append('onclick="showLoadIndicator();"')
    if css_class:
        attributes.append('class="%s"' % css_class)
    for name, value in extra_link_attributes.items():
        attributes.append('%s="%s"' % (name, saxutils.escape(value)))
    return mark_safe(' '.join(attributes))

def rotate_grid(list, columns):
    """Used to make columned lists be ordered by column instead of rows.  For
    example the category list on the front page.
    """

    retval = []
    row_in_retval = 0
    rows = (len(list) + columns - 1) / columns
    while len(retval) < len(list):
        column_from_list = list[row_in_retval:len(list):rows]
        retval.extend(column_from_list)
        row_in_retval += 1
    return retval

def random_string(length):
    return ''.join(random.choice(string.letters) for i in xrange(length))

def make_link(href, label, css_class=None, **extra_link_attributes):
    attrs = make_link_attributes(href, css_class, **extra_link_attributes)
    return mark_safe('<a %s>%s</a>' % (attrs, cgi.escape(label)))

def ensure_dir_exists(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)

def chop_prefix(value, prefix):
    if value.startswith(prefix):
        return value[len(prefix):]
    else:
        return value

def create_post_form(form, request):
    if request.method == 'POST':
        return form(request.connection, request.POST)
    else:
        return form(request.connection)

def select_random(connection, query, count=1):
    row_count = query.count(connection)
    # The following is a completely blind opmitization without any numbers
    # behind it, but my intuition tells me that method 1 is faster when the
    # number of rows in the table is large compared to the count argument.
    # Method two is faster when the number of rows we're looking for is close
    # to the size of the table, and also works if count is greater than the
    # table size.
    if row_count == 0:
        return []
    elif float(count) / row_count < 0.5:
        return random.sample(query.execute(connection), count)
    else:
        return query.order_by('RAND()').limit(count).execute(connection)

def ensure_list(object):
    if hasattr(object, '__iter__'):
        return object
    else:
        return [object]

def get_subscription_url(*links, **kwargs):
    parts = ['url%i=%s' % (index, quote(url)) for (index, url) in
                izip(count(1), links)]
    if kwargs.get('trackback'):
        trackback = kwargs['trackback']
        if isinstance(trackback, (str, unicode)):
            trackback = [trackback]
        parts.extend('trackback%i=%s' % (index, quote(url)) for (index, url) in
                     izip(count(1), trackback))

    attributes = '&'.join(parts)

    if kwargs.get('type') == 'site':
        return settings.SITE_SUBSCRIBE_URL + attributes
    else:
        return settings.SUBSCRIBE_URL + attributes

def unicodify(s, encoding='utf8'):
    """
    Returns a Unicode string.  If u is already Unicode, return it, otherwise
    decode it using the given encoding (default: utf8)
    """
    if isinstance(s, unicode):
        return s
    else:
        return s.decode(encoding)

def donation_decorator (func):
    """ """
    def wrapper (request, *args):
        """ """
        referrer = request.META.get('HTTP_REFERER', '')
        hasCookie = request.COOKIES.get('donate_pitch') or \
            request.COOKIES.get('donate_donated')
        if referrer.startswith(settings.BASE_URL_FULL) or hasCookie:
            response = func(request, *args)
        else:
            response = redirect('/donate', {'next': request.path})
        if not hasCookie:
            response.set_cookie('donate_pitch', 'yes', max_age=None,
                                secure=settings.USE_SECURE_COOKIES or None)
        return response
    return wrapper
