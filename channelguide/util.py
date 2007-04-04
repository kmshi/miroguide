"""Util package.  Used for often used convenience functions. """

from datetime import datetime, timedelta
from itertools import cycle, count
from urllib import quote, urlopen
from urlparse import urlparse
import Queue
import md5
import os
import random
import re
import string
import subprocess
import sys
import threading

from django import shortcuts
from django.template.context import RequestContext
from django.core.mail import send_mail as django_send_mail
from django.conf import settings
from django.http import HttpResponseRedirect, Http404
from sqlalchemy.orm.attributes import InstrumentedList

emailer = None

def render_to_response(request, template_name, context=None, **kwargs):
    """channel guide version of render_to_response.  It passes the template a
    RequestContext object instead of the standard Context object.  
    """
    template_name = 'guide/' + template_name
    return shortcuts.render_to_response(template_name, context,
            context_instance=RequestContext(request), **kwargs)

def import_last_component(name):
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

def make_absolute_url(relative_url, get_data=None):
    return settings.BASE_URL + relative_url + format_get_data(get_data)

def format_get_data(get_data):
    if not get_data:
        return ''
    parts = []
    for key, value in get_data.items():
        parts.append('%s=%s' % (key, quote(value)))
    return '?' + '&'.join(parts)

def get_absolute_url_path(relative_url):
    return urlparse(make_absolute_url(relative_url))[2]

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
        return redirect(request.META['HTTP_REFERER'])
    except KeyError:
        return redirect(settings.BASE_URL)

def send_to_login_page(request):
    login_url = 'accounts/login?next=%s' % get_relative_path(request)
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
    pipe = subprocess.Popen(["identify", "-"], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE)
    pipe.stdin.write(image_data)
    pipe.stdin.close()
    identify_output = pipe.stdout.read()
    returncode = pipe.wait()
    if returncode != 0:
        raise OSError("identify failed with return code %s" % returncode)
    return identify_output.split(" ")[1].lower()

def make_thumbnail(source_path, dest_path, width, height):
    # From the "Pad Out Image" recipe at
    # http://www.imagemagick.org/Usage/thumbnails/
    border_width = max(width, height) / 2
    call_command("convert",  source_path, 
            "-strip",
            "-resize", "%dx%d>" % (width, height), 
            "-gravity", "center", "-bordercolor", "black",
            "-border", "%s" % border_width,
            "-crop", "%dx%d+0+0" % (width, height),
            "+repage", dest_path)

def copy_post_and_files(request):
    data = request.POST.copy()
    data.update(request.FILES)
    return data

def set_cookie(response, key, value, seconds):
    expires_at = datetime.now() + timedelta(seconds=seconds)
    response.set_cookie(key, value, max_age=seconds,
            expires=expires_at.strftime("%a, %d-%b-%Y %H:%M:%S GMT"))

def hash_string(str):
    return md5.new(str).hexdigest()

def get_object_or_404(query, id):
    obj = query.get(id)
    if obj is None:
        raise Http404
    else:
        return obj

def send_mail(title, body, recipient_list, email_from=None):
    global emailer
    if type(recipient_list) is str:
        recipient_list = [recipient_list]
    if emailer is None:
        if not settings.EMAIL_FROM:
            return
        email_func = django_send_mail
    else:
        email_func = emailer
    if email_from is None:
        email_from = settings.EMAIL_FROM
    for email_to in recipient_list:
        email_func(title, body, email_from, [email_to])

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

def call_command(*args):
    pipe = subprocess.Popen(args, stdout=subprocess.PIPE)
    stdout, stderr = pipe.communicate()
    if pipe.returncode != 0:
        raise OSError("call_command with %s has return code %s" % 
                (args, pipe.returncode))
    else:
        return stdout

def url_is_relative(url):
    return '://' not in url and url != '#' and not url.startswith("/")

def make_link_attributes(href, css_class=None, **extra_link_attributes):
    if url_is_relative(href):
        href = make_absolute_url(href)
    attributes = []
    attributes.append('href="%s"' % href)
    if 'onclick' not in extra_link_attributes:
        attributes.append('onclick="showLoadIndicator();"')
    if css_class:
        attributes.append('class="%s"' % css_class)
    for name, value in extra_link_attributes.items():
        attributes.append('%s="%s"' % (name, value))
    return ' '.join(attributes)

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
    return '<a %s>%s</a>' % (attrs, label)

def flatten(*args):
    for obj in args: 
        if type(obj) in (list, tuple, InstrumentedList):
            for i in flatten(*obj):
                yield i
        else: 
            yield obj

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
        return form(request.db_session, request.POST)
    else:
        return form(request.db_session)
