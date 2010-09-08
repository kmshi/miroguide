from datetime import datetime
import logging
import time
import traceback

from django.core.management.base import BaseCommand
from channelguide.channels.models import Channel
from channelguide.channels.management import utils

class Command(BaseCommand):

    def handle(self, **kwargs):
        """Update the items for each channel."""
        utils.set_short_socket_timeout()
        now = datetime.now()
        def callback(channel):
            if channel.state == Channel.SUSPENDED and now.weekday() != 6:
                # only check suspended feeds on Sunday
                return
            if not channel.is_approved() and \
                    channel.state != Channel.SUSPENDED:
                # only check approved/suspended feeds
                return
            if channel.id % 24 != now.hour:
                # check channels throughout the day, some each hour
                return
            try:
                start = time.time()
                channel.update_items()
                length = time.time() - start
                if length > 6:
                    logging.warn("Update too slow for %s: %f" % (channel.url,
                                                                 length))
            except:
                logging.warn("\nError updating items for %s\n\n%s\n" %
                        (channel, traceback.format_exc()))
        utils.spawn_threads_for_channels('updating items', callback, 4)
