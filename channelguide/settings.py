# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.


import os
from datetime import timedelta
from urlparse import urlparse

# We don't actually use the DATABASE_ENGINE variable, but django requires it
# for the test suite.  Set it to dummy to prevent django from complaining.
DATABASE_ENGINE = 'dummy'

# sitespecific.py stores all server specific data. 
from sitespecific import *

TEMPLATE_DEBUG = DEBUG

APPEND_SLASH = False

ADMINS = (
   ('Paul Swartz', 'pswartz@pculture.org'),
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

# Language code for this installation. All choices can be found here:
# http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
# http://blogs.law.harvard.edu/tech/stories/storyReader$15
LANGUAGE_CODE = 'en'

_ = lambda x: x
LANGUAGES = (
    ('en', _("English")),
    ('ar', _("Arabic")),
    ('bn', _("Bengali")),
    ('ca', _("Catalan")),
    ('zh-cn', _("Chinese")), # TODO What to do about Cantonese/Mandarin?
    ('hr', _("Croation")),
    ('da', _("Danish")),
    ('nl', _("Dutch")),
    ('et', _("Estonian")),
    ('fi', _("Finnish")),
    ('fr', _("French")),
    ('de', _("German")),
    ('el', _("Greek")),
    ('he', _("Hebrew")),
    ('hi', _("Hinidi")),
    ('hu', _("Hungarian")),
    ('is', _("Icelandic")),
    ('id', _("Indonesian")),
    ('it', _("Italian")),
    ('ja', _("Japanese")),
    ('ko', _("Korean")),
    ('ku', _('Kurdish (Sorani)')),
    ('lv', _("Latvian")),
    ('lt', _("Lithuanian")),
    ('ms', _("Malay")),
    ('no', _("Norwegian")),
    ('fa', _('Persian')),
    ('pl', _("Polish")),
    ('pt-br', _('Portuguese (Brazillian)')),
    ('pt', _("Portuguese (Portugal)")),
    ('ro', _("Romanian")),
    ('ru', _("Russian")),
    ('sh', _("Serbo-Croatian")),
    ('sk', _("Slovak")),
    ('es', _("Spanish")),
    ('sv', _("Swedish")),
    ('th', _("Thai")),
    ('tr', _("Turkish")),
    ('vi', _("Vietnamese")),
    )

LANGUAGE_MAP = dict(LANGUAGES)

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
    'channelguide.cache.middleware.CacheTimingMiddleware',
    'channelguide.db.middleware.DBMiddleware',
    'channelguide.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'channelguide.cache.middleware.CacheMiddleware',
    'channelguide.guide.middleware.NotificationMiddleware',
    'channelguide.guide.middleware.UserMiddleware',
    'channelguide.guide.middleware.ChannelCountMiddleware',
    'channelguide.guide.middleware.ProfileMiddleware',
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

USE_SECURE_COOKIES = BASE_URL_FULL.startswith('https://')

# URLs

MEDIA_URL = STATIC_BASE_URL + 'media/'
IMAGES_URL = STATIC_BASE_URL + "images/"

# directories
SITE_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SITE_DIR, '..'))

OPTIMIZED_TEMPLATE_DIR = os.path.join(SITE_DIR, 'templates-optimized')
NORMAL_TEMPLATE_DIR = os.path.join(SITE_DIR, 'templates')
def pick_template_dir():
    if not os.path.exists(OPTIMIZED_TEMPLATE_DIR):
        return NORMAL_TEMPLATE_DIR
    source_stat = os.stat(os.path.join(SITE_DIR, 'guide', 'templates'))
    optimized_stat = os.stat(OPTIMIZED_TEMPLATE_DIR)
    if source_stat.st_mtime > optimized_stat.st_mtime:
        return NORMAL_TEMPLATE_DIR
    return OPTIMIZED_TEMPLATE_DIR
TEMPLATE_DIR = pick_template_dir()
EXTERNAL_LIBRARY_DIR = os.path.join(SITE_DIR, 'lib')

STATIC_DIR = os.path.join(ROOT_DIR, 'static')
IMAGES_DIR = os.path.join(STATIC_DIR, 'images')
MEDIA_ROOT = os.path.join(STATIC_DIR, 'media')

IMAGE_DOWNLOAD_CACHE_DIR = os.path.join(ROOT_DIR, 'image-download-cache')

TEMPLATE_DIRS = ( TEMPLATE_DIR, ) # to make django happy

# Channelguide specific settings...
SUBSCRIBE_URL = 'http://subscribe.getmiro.com/?'
SITE_SUBSCRIBE_URL = 'http://subscribe.getmiro.com/site?'
DOWNLOAD_URL = 'http://subscribe.getmiro.com/download'
FORUMS_URL = 'http://www.getmiro.com/forum/categories.php'
BASE_URL_PATH = urlparse(BASE_URL)[2]
AUTH_TOKEN_EXPIRATION_TIME = timedelta(days=1)
MAX_FEATURES = 8

MAX_THREADS = 30
MAX_DB_CONNECTIONS = 5

SOCKET_TIMEOUT = 20
