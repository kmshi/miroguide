from django.core.management.base import NoArgsCommand

from channelguide.featured.models import FeaturedQueue
from channelguide.channels.models import Channel

class Command(NoArgsCommand):

    args = ''

    def handle_noargs(self, **options):
        for state in Channel.APPROVED, Channel.AUDIO:
            FeaturedQueue.objects.shuffle(state)
