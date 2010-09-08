import logging
import traceback
from optparse import make_option

from django.core.management.base import BaseCommand
from channelguide.channels.management import utils

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('-r', '--redownload', action='store_true',
                    help='Redownload existing thumbnails'),
        )

    def handle(self, redownload=False, **kwargs):
        """
        update channel thumbnails.
        """
        utils.set_short_socket_timeout()
        def callback(channel):
            try:
                channel.download_item_thumbnails(redownload)
            except:
                logging.warn("\nerror updating thumbnails for %s\n\n%s\n" %
                             (unicode(channel).encode('utf8'),
                              traceback.format_exc()))
        utils.spawn_threads_for_channels('updating thumbnails', callback, 1)
