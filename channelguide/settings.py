# -*- coding: utf-8 -*-
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
    #('Ben Dean-Kawamura', 'ben@pculture.org'),
    #('Christopher Allan Webber', 'cwebber@pculture.org'),
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

# Language code for this installation. All choices can be found here:
# http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
# http://blogs.law.harvard.edu/tech/stories/storyReader$15
LANGUAGE_CODE = 'en'

_ = lambda x: x
ENGLISH_LANGUAGES = (
    ('en', "English"),
    ('ar', "Arabic"),
    ('bn', "Bengali"),
    ('ca', "Catalan"),
    ('zh-cn', "Chinese"), # TODO What to do about Cantonese/Mandarin?
    ('hr', "Croatian"),
    ('da', "Danish"),
    ('nl', "Dutch"),
    ('et', "Estonian"),
    ('fi', "Finnish"),
    ('fr', "French"),
    ('de', "German"),
    ('el', "Greek"),
    ('he', "Hebrew"),
    ('hi', "Hindi"),
    ('hu', "Hungarian"),
    ('is', "Icelandic"),
    ('id', "Indonesian"),
    ('it', "Italian"),
    ('ja', "Japanese"),
    ('ko', "Korean"),
    ('ku', 'Kurdish (Sorani)'),
    ('lv', "Latvian"),
    ('lt', "Lithuanian"),
    ('ms', "Malay"),
    ('no', "Norwegian"),
    ('fa', 'Persian'),
    ('pl', "Polish"),
    ('pt-br', 'Portuguese (Brazillian)'),
    ('pt', "Portuguese (Portugal)"),
    ('ro', "Romanian"),
    ('ru', "Russian"),
    ('sh', "Serbo-Croatian"),
    ('sk', "Slovak"),
    ('sl', "Slovenian"),
    ('es', "Spanish"),
    ('sv', "Swedish"),
    ('th', "Thai"),
    ('tr', "Turkish"),
    ('vi', "Vietnamese"),
    )

LANGUAGES = (
    ('en', u"English"),
    ('ar', u"العربية"),
    ('bn', u"বাংলা"),
    ('ca', u"català"),
    ('zh-cn', u"廣東話"),
    ('hr', u"Hrvatski"),
    ('da', u"dansk"),
    ('nl', u"Nederlands"),
    ('et', u"eesti keel"),
    ('fi', u"suomi"),
    ('fr', u"français"),
    ('de', u"Deutsch"),
    ('el', u"ελληνικά"),
    ('he', u"עברית / עִבְרִית"),
    ('hi', u"हिन्दी"),
    ('hu', u"magyar"),
    ('is', u"Íslenska"),
    ('id', u"Bahasa Indonesia"),
    ('it', u"italiano"),
    ('ja', u"日本語"),
    ('ko', u"한국어"),
    ('ku', u"Kurdí"),
    ('lv', u"latviešu valoda"),
    ('lt', u"lietuvių kalba"),
    ('ms', u"Bahasa melayu"),
    ('no', u"Norsk"),
    ('fa', u"فارسى"),
    ('pl', u"polski"),
    ('pt-br', u"português (brazil)"),
    ('pt', u"português (portugal)"),
    ('ro', u"român"),
    ('ru', u"Русский язык"),
    ('sh', u"Hrvatski"),
    ('sk', u"slovenčina"),
    ('sl', u"slovenščina"),
    ('es', u"español"),
    ('sv', u"Svenska"),
    ('th', u"ภาษาไทย"),
    ('tr', u"Türkçe"),
    ('vi', u"tiếng việt"),
    )

ENGLISH_LANGUAGE_MAP = dict(ENGLISH_LANGUAGES)
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
