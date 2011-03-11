
# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

"""Util package.  Used for often used convenience functions. """

from itertools import cycle, count, izip
from urllib import quote, urlopen, unquote_plus
from xml.sax import saxutils
import Queue
import cgi
import logging
import md5
import os
import re
import random
import string
import subprocess
import sys
import textwrap
import threading
import urllib
import socket # for socket.error

from django import shortcuts
from django.template.context import RequestContext
from django.core.mail import send_mail as django_send_mail
from django.core import cache
from django.conf import settings
from django.utils.http import urlquote
from django.utils.translation import ugettext as _
from django.http import HttpResponseRedirect

from django_bitly.models import Bittle, StringHolder

try:
    from django.utils.safestring import mark_safe
    mark_safe = mark_safe # fix pyflakes error
except ImportError:
    mark_safe = lambda x: x


# sharing urls
DELICIOUS_URL = "http://del.icio.us/post?v=4&noui&jump=close&url=%s&title=%s"
DIGG_URL = "http://digg.com/submit/?url=%s&title=%s&media=video"
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
    key = 'bitly_shorten:%s' % md5.new(url).hexdigest()
    shortURL = cache.cache.get(key)
    if shortURL is not None:
        return shortURL
    try:
        sh, created = StringHolder.objects.get_or_create(absolute_url=url)
    except StringHolder.MultipleObjectsReturned:
        sh = StringHolder.objects.filter(absolute_url=url)[0]
        StringHolder.objects.filter(id!=sh.id, absolute_url=url).delete()
    for i in range(5):
        try:
            b = Bittle.objects.bitlify(sh)
        except (ValueError, IOError, KeyError):
            continue
        else:
            # memcached has a 30 day limit
            cache.cache.set(key, b.shortUrl, 3600 * 24 * 30)
            return b.shortUrl
    return url

def get_share_links(url, name):
    share_delicious = DELICIOUS_URL % (quote(url),
                                       quote(name.encode('utf8')))
    share_digg = DIGG_URL % (quote(url, ''), quote(name.encode('utf8'), ''))
    share_reddit = REDDIT_URL % (quote(url), quote(name.encode('utf8')))
    share_stumbleupon = STUMBLEUPON_URL % (quote(url),
                                           quote(name.encode('utf8')))
    share_facebook = FACEBOOK_URL % (quote(url))
    share_twitter = TWITTER_URL % (
        _('Watching in Miro: %s') % bitly_shorten(url)).replace(' ', '+')

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
    return shortcuts.render_to_response(
        template_name,
        context,
        context_instance=RequestContext(request),
        **kwargs)

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

def make_url(relative_url, get_data=None, ignore_qmark=False):
    if (not ignore_qmark) and '?' in relative_url: # a query
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
        if settings.LOGIN_URL in referrer:
            raise KeyError
        return redirect(referrer)
    except KeyError:
        return redirect(settings.BASE_URL)

def make_qs(**query_dict):
    parts = []
    for key, value in query_dict:
        parts.append('%s=%s' % (quote(key, safe=''), quote(value, safe='')))
    return '?' + parts.join('&')


def copy_obj(dest_path, file_obj):
    # naive implementaton
    file_obj.seek(0)
    f = open(dest_path, 'wb')
    try:
        f.write(file_obj.read())
    finally:
        f.close()

def get_image_extension(image_file):
    image_file.seek(0)
    try:
        identify_output = call_command('identify', '-',
                                       data=image_file)
    except EnvironmentError:
        raise ValueError('not an image we could identify')
    if identify_output is '':
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
    tries = 5
    while True:
        try:
            conn.put(settings.S3_BUCKET,
                     settings.S3_PATH + subpath,
                     obj,
                     {'Content-Type': content_type,
                      'x-amz-acl': 'public-read'})
        except:
            tries -= 1
            if not tries:
                raise
        else:
            return


def make_thumbnail(source_path, dest_path, width, height):
    # From the "Pad Out Image" recipe at
    # http://www.imagemagick.org/Usage/thumbnails/
    border_width = max(width, height) / 2
    try:
        call_command("convert",  source_path,
                     "-strip", '-flatten',
                     "-resize", "%dx%d>" % (width, height),
                     "-gravity", "center", "-bordercolor", "black",
                     "-border", "%s" % border_width,
                     "-crop", "%dx%d+0+0" % (width, height),
                     "+repage", dest_path)
    except EnvironmentError:
        logging.exception('error resizing image')
        raise ValueError('could not resize image')

def hash_string(str):
    return md5.new(str.encode('utf8')).hexdigest()

def send_mail(title, body, recipient_list, email_from=None, break_lines=True):
    if break_lines:
        body = '\n'.join(textwrap.fill(p) for p in body.split('\n'))
    if email_from is None:
        email_from = settings.EMAIL_FROM
    for email_to in ensure_list(recipient_list):
        try:
            django_send_mail(title, body, email_from, [email_to])
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
            pipe.stdin.write(data.read())
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

def ensure_list(object):
    if hasattr(object, '__iter__'):
        return object
    else:
        return [object]

def get_subscription_url(*links, **kwargs):
    parts = ['url%i=%s' % (index, quote(url)) for (index, url) in
                izip(count(1), links)]
    for extraName in ('trackback', 'section'):
        if kwargs.get(extraName):
            extra = kwargs[extraName]
            if isinstance(extra, (str, unicode)):
                extra = [extra]
            parts.extend('%s%i=%s' % (extraName, index, quote(value)) for (index, value) in
                         izip(count(1), extra))

    attributes = '&'.join(parts)

    if kwargs.get('type') == 'site':
        return settings.SITE_SUBSCRIBE_URL + attributes
    else:
        return settings.SUBSCRIBE_URL + attributes


class LiarOpener(urllib.FancyURLopener):
    """
    Some APIs (*cough* vimeo *cough) don't allow urllib's user agent
    to access their site.

    (Why on earth would you ban Python's most common url fetching
    library from accessing an API??)
    """
    version = (
        'Mozilla/5.0 (X11; U; Linux x86_64; rv:1.8.1.6) Gecko/20070802 Firefox')


def open_url_while_lying_about_agent(url):
    opener = LiarOpener()
    return opener.open(url)

def copy_function_metadata(wrapper, func):
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper
