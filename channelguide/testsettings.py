# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

import os

from settings import *

MEDIA_ROOT = os.path.join(STATIC_DIR, "test-media")
MEDIA_URL = 'http://localhost:8000/test-media/'
IMAGE_DOWNLOAD_CACHE_DIR = os.path.join(ROOT_DIR, 'test-image-download-cache')
