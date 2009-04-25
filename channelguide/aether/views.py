# Copyright (c) 2009 Michael C. Urbanski
# See LICENSE for details.

from datetime import datetime
from xml.dom.minidom import Document

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
    try:
        ChannelSubscription.bulk_delete (
            channel_id=cid, user_id=request.user.id        
        ).execute (request.connection)
        
        ChannelSubscriptionDelta.insert (
            ChannelSubscriptionDelta (
                user_id=request.user.id, channel_id=cid, mod_type=-1
            ),
            request.connection
        )
    except LookupError:
        raise Http404 ()

    return HttpResponseRedirect ('/feeds/%s' % cid)

# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# CHANGE TO POST ONCE YOU AJAX-IFY!!!!!!!!!!!!!!!!!!!!!
@login_required
def add_channel_subscription (request, cid):
    if not ChannelSubscription.query (channel_id=cid, user_id=request.user.id).count (request.connection):
        ChannelSubscription.insert (
            ChannelSubscription (user=request.user, channel_id=cid),
           request.connection
        )

        ChannelSubscriptionDelta.insert (
            ChannelSubscriptionDelta (user_id=request.user.id, channel_id=cid),
            request.connection
        )

    return HttpResponseRedirect ('/feeds/%s' % cid)

# JUST A DEMONSTRATION OF THE CONCEPT!!!!!!!!!!!!!!!!!!
# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# NOT IDEMPOTENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# CHANGE TO POST ONCE YOU AJAX-IFY!!!!!!!!!!!!!!!!!!!!!
@login_required
def queue_download (request, item_id):
    if not DownloadRequest.query (item_id=item_id, user_id=request.user.id).count (request.connection):
        try:
            DownloadRequest.insert (
                DownloadRequest (user=request.user, item_id=item_id),
                request.connection
            )

            DownloadRequestDelta.insert (
                DownloadRequestDelta (user=request.user, item_id=item_id),
                request.connection
            )
        except LookupError:
            raise Http404 ()
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
# decorating these classes would be presumptuous at this point...
ITEM_PROPS = [
    'id',
    'channel_id',
    'name',
    'date',
    'guid',
    'description',
    'url',
    'mime_type',
    'size',
    'thumbnail_url'
]

CHANNEL_PROPS = [
    'id',
    'name',
    'description',
    'license',
    'publisher',
    'url',
    'website_url'
]

#@login_required
def get_user_deltas (request, uid, start_time, end_time):
    start_time = datetime.utcfromtimestamp (float (start_time))
    end_time = datetime.utcfromtimestamp (float (end_time))

    if end_time < start_time:
        raise Http404 ()

    user = request.user

    # Remove
    from channelguide.guide.models.user import User
    user = User.query (id=uid).get (request.connection)

    #

    #uid = request.user.id

    user.join ('subscriptions').execute (request.connection)

    sub_deltas = []
    item_deltas = []

    sub_ids = [s.channel_id for s in user.subscriptions]

    d = Document ()
    root = d.createElement('aether')
    d.appendChild (root)

    if (len (sub_ids)):
        sub_deltas = request.connection.execute (
            """SELECT sum(mod_type) AS mod_sum, channel_id
                 FROM aether_channel_subscription_delta
                 WHERE created_at > %s AND created_at <= %s
                 AND user_id = %s
               GROUP BY channel_id
               HAVING mod_sum != 0
               ORDER BY channel_id""", (start_time, end_time, uid,)
        )

        item_deltas = request.connection.execute (
            """SELECT sum(mod_type) AS mod_sum, acid.item_id, acid.channel_id
                 FROM aether_channel_item_delta AS acid
               JOIN aether_channel_subscription AS acs ON acid.channel_id=acs.channel_id
                 WHERE acid.channel_id IN (%s)
                 AND (acid.created_at > '%s' AND acid.created_at <= '%s')
                 OR (acs.created_at > '%s' AND acs.created_at <= '%s')
               GROUP BY item_id
               HAVING mod_sum != 0
               ORDER BY item_id"""
            % (
                ','.join ([str(s) for s in sub_ids]),
                start_time, end_time,
                start_time, end_time
            )
        )

        if sub_deltas:
            # I'm a relative python newbie, just wanted to play with list comprehensions!
            new_sub_ids = [s[1] for s in sub_deltas if s[0] > 0]
            removed_sub_ids = [s[1] for s in sub_deltas if s[0] < 0]

            channels = d.createElement ('channels')

            for si in removed_sub_ids:
                sub = d.createElement ('channel')
                sub.setAttribute ('action', 'removed')
                sub.appendChild (to_element (d, 'id', si))
                channels.appendChild (sub)

            if new_sub_ids:
                subs = Channel ().query ().where (
                    Channel.c.id.in_ (new_sub_ids)
                ).execute (request.connection)

                for s in subs:
                    sub = d.createElement ('channel')
                    sub.setAttribute ('action', 'added')

                    for cp in CHANNEL_PROPS:
                        sub.appendChild (to_element (d, cp, getattr(s, cp)))

                    sub.appendChild (
                        to_element (d, 'thumb_url', s.thumb_url_245_164 ())
                    )

                    channels.appendChild (sub)

            root.appendChild (channels)

        if item_deltas:
            new_item_ids = [i[1] for i in item_deltas if i[0] > 0]
            removed_item_ids = [i[1] for i in item_deltas if i[0] < 0]

            items = d.createElement ('items')

            for ni in removed_item_ids:
                i = d.createElement ('item')
                i.setAttribute ('action', 'removed')
                i.appendChild (to_element (d, 'id', ni))
                items.appendChild (i)

            if new_item_ids:
                new_items = Item ().query ().where (
                    Item.c.id.in_(new_item_ids)
                ).execute (request.connection)

                for ni in new_items:
                    i = d.createElement ('item')
                    i.setAttribute ('action', 'added')

                    for ip in ITEM_PROPS:
                        i.appendChild (to_element (d, ip, getattr(ni, ip)))

                    items.appendChild (i)

            root.appendChild (items)

    return HttpResponse(d.toxml (), mimetype='application/xml')

def to_element (doc, name, val):
    node = doc.createElement (name)

    if val is not None:
        node.appendChild (doc.createTextNode (unicode(val)))
        
    return node
