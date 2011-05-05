# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

#DATABASE_NAME = FILL ME IN
#DATABASE_USER = FILL ME IN
#DATABASE_PASSWORD = FILL ME IN
#DATABASE_HOST = FILL ME IN
#DATABASE_PORT = FILL ME IN

MEMCACHED_SERVERS = []

# name to put on outgoing emails
EMAIL_FROM = 'kmshi_array@yahoo.com'

# Local time zone for this installation. All choices can be found here:
# http://www.postgresql.org/docs/current/static/datetime-keywords.html#DATETIME-TIMEZONE-SET-TABLE
# Example: US/Eastern
#TIME_ZONE = FILL ME IN

# Make this unique, and don't share it with anybody.
# Example: 'sdzqwb$$dw0ojx^i(^wkskp3c@xu4unq$qyzj2_5ng3d05a+74'
#SECRET_KEY = FILL ME IN

BASE_URL = '/'
BASE_URL_FULL = BASE_URL
# Change this if the location for static stuff (images, javascript, css files)
# is separate from the rest of the URLs.
STATIC_BASE_URL = BASE_URL

# Use to enable google analytics
GOOGLE_ANALYTICS_UA = None

# String to prefix cache entries with.  Any string unique to this server will
# do.
CACHE_PREFIX = 'gfw'
DISABLE_CACHE = False
DEBUG = True

USE_S3 = False
S3_ACCESS_KEY = None
S3_SECRET_KEY = None
S3_BUCKET = None
S3_PATH = None

BITLY_USERNAME = None
BITLY_API_KEY = None
