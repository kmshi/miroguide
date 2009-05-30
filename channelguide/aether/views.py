# Copyright (c) 2009 Michael C. Urbanski
# See LICENSE for details.

from simplejson import dumps

from django.http import Http404, HttpResponseRedirect, HttpResponse
from channelguide.guide.auth import login_required

from channelguide.guide.models.item import Item
from channelguide.guide.models.channel import Channel

from channelguide.aether.models import (
    ChannelSubscription, ChannelSubscriptionDelta,
    DownloadRequest, DownloadRequestDelta
)

from channelguide.aether.dbutils import user_lock_required

# JUST A DEMONSTRATION OF THE CONCEPT!!!!!!!!!!!!!!!!!!
# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# CHANGE TO POST ONCE YOU AJAX-IFY!!!!!!!!!!!!!!!!!!!!!
@login_required
@user_lock_required
def remove_channel_subscription (request, cid):
    c = request.connection

    if subscribed (request.user.id, cid, c):
        ChannelSubscription.bulk_delete (
            channel_id=cid, user_id=request.user.id
        ).execute (c)

        ChannelSubscriptionDelta.insert (
            ChannelSubscriptionDelta (
                user_id=request.user.id, channel_id=cid, mod_type=-1
            ), c
        )

    return HttpResponseRedirect ('/feeds/%s' % cid)

# JUST A DEMONSTRATION OF THE CONCEPT!!!!!!!!!!!!!!!!!!
# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# CHANGE TO POST ONCE YOU AJAX-IFY!!!!!!!!!!!!!!!!!!!!!
@login_required
@user_lock_required
def add_channel_subscription (request, cid):
    c = request.connection

    try:
        #Lazy way to generate a LookupError if the channel doesn't exist, FIX ME.
        chan = Channel.get (c, cid)
    except Exception as e:
        if isinstance (e, LookupError):
            raise Http404 ()
        else:
            raise
        
    if not subscribed (request.user.id, cid, c):
        ChannelSubscription.insert (
            ChannelSubscription (user=request.user, channel_id=cid), c
        )

        ChannelSubscriptionDelta.insert (
            ChannelSubscriptionDelta (user_id=request.user.id, channel_id=cid), c
        )
        
    return HttpResponseRedirect ('/feeds/%s' % cid)

@login_required
@user_lock_required
def queue_download (request, item_id):
    c = request.connection

    try:
        #Lazy way to generate a LookupError if the item doesn't exist, FIX ME.
        item = Item.get (c, item_id)
    except Exception as e:
        if isinstance (e, LookupError):
            raise Http404 ()
        else:
            raise
        
    ret = {"status": "queued"}

    if not queued_for_download (request.user.id, item_id, c):
        DownloadRequest.insert (
            DownloadRequest (user=request.user, item_id=item_id),
            request.connection
        )

        DownloadRequestDelta.insert (
            DownloadRequestDelta (user=request.user, item_id=item_id),
            request.connection
        )
    else:
        ret['status'] = "dequeued"

    return HttpResponse (dumps (ret), mimetype="application/json")

@login_required
@user_lock_required
def cancel_download (request, item_id):
    ret = {"status": "dequeued"}

    if queued_for_download (request.user.id, item_id, request.connection):
        DownloadRequest.bulk_delete (
            user_id=request.user.id, item_id=item_id
        ).execute (request.connection)

        DownloadRequestDelta.insert (
            DownloadRequestDelta (user=request.user, item_id=item_id, mod_type=-1),
            request.connection
        )
    else:
        ret = {"status": "queued"}

    return HttpResponse (dumps (ret), mimetype="application/json")

        
def subscribed (user_id, channel_id, conn):
    query = ChannelSubscription.query ().where (user_id=user_id, channel_id=channel_id)

    if query.count (conn):
        return True

    return False


def queued_for_download (user_id, item_id, conn):
    query = DownloadRequest.query ().where (user_id=user_id, item_id=item_id)

    if query.count (conn):
        return True

    return False
