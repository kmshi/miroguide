
# sitespecific.py stores all server specific data. 
import os

from sitespecific import *
from urlparse import urlparse

DEBUG = True
TEMPLATE_DEBUG = DEBUG

APPEND_SLASH = False

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

# Language code for this installation. All choices can be found here:
# http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
# http://blogs.law.harvard.edu/tech/stories/storyReader$15
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/admin-media/'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'channelguide.db.middleware.DBMiddleware',
    'channelguide.sessions.middleware.SessionMiddleware',
    'channelguide.guide.middleware.UserMiddleware',
)

ROOT_URLCONF = 'channelguide.guide.urls.root'

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "channelguide.context_processors.guide",
)

INSTALLED_APPS = (
    'channelguide.guide',
    'channelguide.db',
    'channelguide.sessions',
)

# URLs

MEDIA_URL = BASE_URL + "media/"
IMAGES_URL = BASE_URL + "images/"

# directories
SITE_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SITE_DIR, '..'))

TEMPLATE_DIR = os.path.join(SITE_DIR, 'templates')

STATIC_DIR = os.path.join(ROOT_DIR, 'static')
IMAGES_DIR = os.path.join(STATIC_DIR, 'images')
MEDIA_ROOT = os.path.join(STATIC_DIR, 'media')

IMAGE_DOWNLOAD_CACHE_DIR = os.path.join(ROOT_DIR, 'image-download-cache')

TEMPLATE_DIRS = ( TEMPLATE_DIR, ) # to make django happy

# Channelguide specific settings...
SUBSCRIBE_URL = 'http://subscribe.getdemocracy.com/?url1=%(url)s'
BASE_URL_PATH = urlparse(BASE_URL)[2]
SOCKET_TIMEOUT = 10

import socket
socket.setdefaulttimeout(SOCKET_TIMEOUT)
