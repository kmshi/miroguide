
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
    'channelguide.cache.middleware.CacheMiddleware',
    'channelguide.db.middleware.DBMiddleware',
    'channelguide.sessions.middleware.SessionMiddleware',
    'channelguide.guide.middleware.UserMiddleware',
    'channelguide.guide.middleware.ChannelCountMiddleware',
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

MEDIA_URL = STATIC_BASE_URL + "media/"
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
SUBSCRIBE_URL = 'http://subscribe.getdemocracy.com/?url1=%(url)s'
FORUMS_URL = 'http://forum.getdemocracy.com/'
BASE_URL_PATH = urlparse(BASE_URL)[2]
AUTH_TOKEN_EXPIRATION_TIME = timedelta(days=1)
MAX_FEATURES = 15

MAX_THREADS = 30
MAX_DB_CONNECTIONS = 5

SOCKET_TIMEOUT = 20
