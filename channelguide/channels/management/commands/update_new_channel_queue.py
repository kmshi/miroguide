from django.core.management.base import BaseCommand
from channelguide.channels.models import Channel, LastApproved

class Command(BaseCommand):

    def handle(self, **kwargs):
        """
        Update the cg_channel_last_approved table to include the next
        most-recently approved channel.
        """
        timestamp = LastApproved.objects.timestamp()
        new_channels = Channel.objects.filter(
            approved_at__gt=timestamp).order_by('approved_at')
        if new_channels.count():
            last_approved = LastApproved.objects.get()
            last_approved.delete()
            if kwargs.get('verbosity', 0) > 1:
                print 'Updating last approved time to %s' % (
                    new_channels[0].approved_at)
            LastApproved(timestamp=new_channels[0].approved_at).save()
