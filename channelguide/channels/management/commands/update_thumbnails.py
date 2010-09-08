import logging
from optparse import make_option
import traceback
from django.core.management.base import BaseCommand
from channelguide.channels.management import utils

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('-o', '--overwrite', action='store_true',
                    help='Overwrite existing thumbnails'),)

    def handle(self, *sizes, **kwargs):
        overwrite = kwargs.pop('overwrite', False)
        if len(sizes) == 0:
            sizes = None
        for channel in utils.all_channel_iterator('update thumbnails'):
            try:
                channel.update_thumbnails(overwrite, None)
            except:
                logging.warn('error updating thumbnails for %i:\n%s' % (
                        channel.id,
                        traceback.format_exc()))
