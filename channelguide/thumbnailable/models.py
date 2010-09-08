# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

"""thumbnail.py.  Defines the ThumbnailManager class which manages thumbnails
for Channel and Item objects.
"""

from urlparse import urljoin
import os.path

from django.conf import settings
from django.db import models

from channelguide import util

class Thumbnailable(models.Model):
    """Mixin class that gives thumbnail capabilities.

    This class create multiple thumbnails from a given full-sized image.

    Classes using this mixin must define THUMBNAIL_DIR and THUMBNAIL_SIZES as
    class attributes.  The should also have a thumbnail_extension attribute
    that gets saved to the DB.
    """

    thumbnail_extension = models.CharField(max_length=8, null=True,
                                           default=None)

    class Meta:
        abstract = True

    def get_filename(self, subdir=None):
        if not self.pk:
            raise ValueError("Must be saved first")
        elif subdir == 'original':
            return "%d.%s" % (self.id, self.thumbnail_extension)
        else:
            return '%d.jpeg' % self.id

    def thumb_path(self, subdir):
        thumb_dir = os.path.join(settings.MEDIA_ROOT, self.THUMBNAIL_DIR,
                subdir)
        if not os.path.exists(thumb_dir):
            os.makedirs(thumb_dir)
        return os.path.join(thumb_dir, self.get_filename(subdir))

    def get_missing_image_url(self, width, height):
        return settings.IMAGES_URL + 'missing.png'

    def thumb_url(self, width, height):
        if not self.thumbnail_exists():
            return self.get_missing_image_url(width, height)
        return urljoin(settings.MEDIA_URL, '%s/%dx%d/%s' %
                (self.THUMBNAIL_DIR, width, height, self.get_filename()))

    def _save_to_s3(self, path):
        if not settings.USE_S3:
            return
        if 'original' in path:
            subpath = self.THUMBNAIL_DIR + '/' + path + '/' + self.get_filename('original')
        else:
            subpath = self.THUMBNAIL_DIR + '/' + path + '/' + self.get_filename()
        content_type = 'image/' + os.path.splitext(subpath)[1][1:]
        util.push_media_to_s3(subpath, content_type)

    def _save_original_thumbnail(self, image_file):
        dest = self.thumb_path('original')
        util.copy_obj(dest, image_file)
        self._save_to_s3('original')

    def _make_thumbnail(self, image_file, width, height):
        source = self.thumb_path('original')
        dest = self.thumb_path("%dx%d" % (width, height))
        util.make_thumbnail(source, dest, width, height)
        self._save_to_s3('%dx%d' % (width, height))

    def save_thumbnail(self, image_file):
        """Save the thumbnail for this image.  image_file should be a file-like
        object containing the full-sized image.
        """

        self.thumbnail_extension = util.get_image_extension(image_file)
        image_file.seek(0)
        self._save_original_thumbnail(image_file)
        for width, height in self.THUMBNAIL_SIZES:
            image_file.seek(0)
            self._make_thumbnail(image_file, width, height)
        self.save()

    def refresh_thumbnails(self, overwrite=False, sizes=None):
        """Recreate the thumbnails using the original data."""

        if self.thumbnail_extension is None:
            return
        image_file = file(self.thumb_path('original'))
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
                self._make_thumbnail(image_file, width, height)

    def thumbnail_exists(self):
        return self.thumbnail_extension is not None
