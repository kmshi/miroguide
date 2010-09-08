import logging
import traceback
from django.core.management.base import BaseCommand
from channelguide.search.models import ChannelSearchData
from channelguide.channels.management import utils

class Command(BaseCommand):

    def handle(self, **kwargs):
        for channel in utils.all_channel_iterator('update search data'):
            try:
                ChannelSearchData.objects.update(channel)
            except:
                logging.warn('error updating search data for %i:\n%s' % (
                        channel.id,
                        traceback.format_exc()))
