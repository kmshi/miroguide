# No actual models; this just replaces the cache-resetting functionality of
# thet old dbwatcher module

import time

from django.db.models.signals import post_save
from django.core import cache

def handle_save(sender=None, instance=None, **kwargs):
    # reset the table key, so cached pages will not find the old caches
    now = time.time()
    if sender.__name__ not in (
        'User',
        'Permission',
        'Group',
        'ContentType',
        'Session',
        'Site',
        'Subscription',
        'UserProfile',
        ):
        cache.cache.set('namespace', now)
    if sender.__name__ == 'Channel':
        cache.cache.set('Channel:%i' % instance.pk, now)
    elif sender.__name__ == 'Item':
        cache.cache.set('Channel:%i' % instance.pk, now)

post_save.connect(handle_save)
