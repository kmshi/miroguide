import os

from settings import *

MEDIA_ROOT = os.path.abspath(os.path.join("static", "test-media"))
MEDIA_URL = 'http://localhost:8000/test-media/'
