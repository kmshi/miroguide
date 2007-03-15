"""thumbnail.py.  Defines the ThumbnailManager class which manages thumbnails
for Channel and Item objects.
"""

from StringIO import StringIO
from urlparse import urljoin
import os

from django.conf import settings

from channelguide import util

class Thumbnailable(object):
    """Mixin class that gives thumbnail capabilities.

    This class create multiple thumbnails from a given full-sized image.
    
    Classes using this mixin must define THUMBNAIL_DIR and THUMBNAIL_SIZES as
    class attributes.
    """

    def get_filename(self):
        if self.id is None:
            raise ValueError("Must be saved first")
        elif self.thumbnail_extension is None:
            return "missing.png"
        else:
            return "%d.%s" % (self.id, self.thumbnail_extension)

    def thumb_path(self, subdir):
        thumb_dir = os.path.join(settings.MEDIA_ROOT, self.THUMBNAIL_DIR, 
                subdir)
        if not os.path.exists(thumb_dir):
            os.makedirs(thumb_dir)
        return os.path.join(thumb_dir, self.get_filename())

    def thumb_url(self, width, height):
        return urljoin(settings.MEDIA_URL, '%s/%dx%d/%s' % 
                (self.THUMBNAIL_DIR, width, height, self.get_filename()))

    def _save_original_thumbnail(self, image_data):
        dest = self.thumb_path('original')
        util.write_file(dest, image_data)

    def _make_thumbnail(self, image_data, width, height):
        source = self.thumb_path('original')
        dest = self.thumb_path("%dx%d" % (width, height))
        util.make_thumbnail(source, dest, width, height)

    def save_thumbnail(self, image_data):
        """Save the thumbnail for this image.  image_data should be a string
        containing the full-sized image.
        """

        self.thumbnail_extension = util.get_image_extension(image_data)
        self._save_original_thumbnail(image_data)
        for width, height in self.THUMBNAIL_SIZES:
            self._make_thumbnail(image_data, width, height)

    def refresh_thumbnails(self, overwrite=False, sizes=None):
        """Recreate the thumbnails using the original data."""

        if self.thumbnail_extension is None:
            return
        image_data = util.read_file(self.thumb_path('original'))
        if sizes is None:
            sizes = self.THUMBNAIL_SIZES
        else:
            sizes = [s.split('x') for s in sizes]
            sizes = [(int(s[0]), int(s[1])) for s in sizes]
        for width, height in sizes:
            if (width, height) not in self.THUMBNAIL_SIZES:
                continue
            thumb_path = self.thumb_path("%dx%d" % (width, height))
            if overwrite or not os.path.exists(thumb_path):
                self._make_thumbnail(image_data, width, height)
