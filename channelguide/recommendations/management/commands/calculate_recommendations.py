from django.core.management.base import BaseCommand

class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        """
        Calculate the item-item channel recomendations.
        """
        from channelguide.recommendations.models import Similarity
        if len(args) > 2 and args[2] == 'full':
            Similarity.objects.recalculate_all()
        else:
            Similarity.objects.recalculate_recent()
