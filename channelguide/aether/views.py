# Copyright (c) 2009 Michael C. Urbanski
# See LICENSE for details.

from django.http import Http404, HttpResponseRedirect, HttpResponse
from channelguide.guide.auth import login_required

from channelguide.guide.models.item import Item
from channelguide.guide.models.channel import Channel

from channelguide.aether.models import (
    ChannelSubscription, ChannelSubscriptionDelta,
    DownloadRequest, DownloadRequestDelta
)

# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# CHANGE TO POST ONCE YOU AJAX-IFY!!!!!!!!!!!!!!!!!!!!!
@login_required
def remove_channel_subscription (request, cid):
    c = request.connection
    c.begin ()

    try:
        if c.execute (
            '''SELECT COUNT(*) FROM aether_channel_subscription
                 WHERE user_id = %s AND channel_id = %s
               FOR UPDATE''', (request.user.id, cid,))[0][0]:

            ChannelSubscription.bulk_delete (
                channel_id=cid, user_id=request.user.id
            ).execute (c)

            ChannelSubscriptionDelta.insert (
                ChannelSubscriptionDelta (
                    user_id=request.user.id, channel_id=cid, mod_type=-1
                ), c
            )

            c.commit ()
    except Exception as e:
        c.rollback ()

        if isinstance (e, LookupError):
            raise Http404 ()
        else:
            raise

    return HttpResponseRedirect ('/feeds/%s' % cid)

# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# CHANGE TO POST ONCE YOU AJAX-IFY!!!!!!!!!!!!!!!!!!!!!
@login_required
def add_channel_subscription (request, cid):
    c = request.connection
    c.begin ()
    
    try:
        #Lazy way to generate a LookupError if the channel doesn't exist, FIX ME.
        chan = Channel.get (c, cid)

        if not c.execute (
            '''SELECT COUNT(*) FROM aether_channel_subscription
                 WHERE user_id = %s AND channel_id = %s
               FOR UPDATE''', (request.user.id, cid,))[0][0]:

            ChannelSubscription.insert (
                ChannelSubscription (user=request.user, channel_id=cid), c
            )

            ChannelSubscriptionDelta.insert (
                ChannelSubscriptionDelta (user_id=request.user.id, channel_id=cid), c
            )

        c.commit ()
    except Exception as e:
        c.rollback ()
        
        if isinstance (e, LookupError):
            raise Http404 ()
        else:
            raise

    return HttpResponseRedirect ('/feeds/%s' % cid)

# JUST A DEMONSTRATION OF THE CONCEPT!!!!!!!!!!!!!!!!!!
# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# CHANGE TO POST ONCE YOU AJAX-IFY!!!!!!!!!!!!!!!!!!!!!
@login_required
def queue_download (request, item_id):
    c = request.connection
    c.begin ()

    try:
        #Lazy way to generate a LookupError if the item doesn't exist, FIX ME.
        item = Item.get (c, item_id)
        
        if not c.execute ('''SELECT COUNT(*) FROM aether_download_request
                               WHERE user_id = %s AND item_id = %s
                             FOR UPDATE''', (request.user.id, item_id,))[0][0]:
                                 
            DownloadRequest.insert (
                DownloadRequest (user=request.user, item_id=item_id),
                request.connection
            )

            DownloadRequestDelta.insert (
                DownloadRequestDelta (user=request.user, item_id=item_id),
                request.connection
            )
        c.commit ()
    except Exception as e:
        c.rollback ()

        if isinstance (e, LookupError):
            raise Http404 ()
        else:
            raise
    
    # THIS IS CRAP, CHANGE IT WHEN AJAX-IFIED!!!!!!!!!!
    return HttpResponseRedirect (
        '/feeds/%s' % (Item.query (id=item_id).get (request.connection).channel_id)
    )

# JUST A DEMONSTRATION OF THE CONCEPT!!!!!!!!!!!!!!!!!!
# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# CHANGE TO POST ONCE YOU AJAX-IFY!!!!!!!!!!!!!!!!!!!!!
@login_required
def cancel_download (request, item_id):
    try:
        DownloadRequest.bulk_delete (
            user_id=request.user.id, item_id=item_id
        ).execute (request.connection)

        DownloadRequestDelta.insert (
            DownloadRequestDelta (user=request.user, item_id=item_id, mod_type=-1),
            request.connection
        )
    except LookupError:
        raise Http404 ()

    # THIS IS CRAP, CHANGE IT WHEN AJAX-IFIED!!!!!!!!!!
    return HttpResponseRedirect (
        '/feeds/%s' % (Item.query (id=item_id).get (request.connection).channel_id)
    )
