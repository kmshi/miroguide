# Copyright (c) 2009 Michael C. Urbanski
# See LICENSE for details.

from IPy import IP
from uuid import uuid4
from time import mktime
from datetime import datetime
from xml.dom.minidom import Document

from django.http import Http404, HttpResponseRedirect, HttpResponse
from channelguide.guide.auth import login_required

from channelguide.guide.models.item import Item
from channelguide.guide.models.channel import Channel
from channelguide.aether.models import Client

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

@login_required
def get_user_deltas (request, client_id):

    user = request.user

    try:
        client = Client.query (
            user_id=user.id, client_id=client_id
        ).get (request.connection)
    except:
        raise Http404 ()

    end_time = datetime.now ()
    start_time = client.last_updated
    
    if end_time < start_time:
        raise Http404 ()

    user.join ('subscriptions').execute (request.connection)

    sub_deltas = []
    item_deltas = []

    sub_ids = [s.channel_id for s in user.subscriptions]

    d = Document ()

    root = d.createElement('aether')
    set_attribute (root, 'time', str (mktime(end_time.timetuple ())))

    d.appendChild (root)

    if (len (sub_ids)):
        sub_deltas = request.connection.execute (
            """SELECT sum(mod_type) AS mod_sum, channel_id
                 FROM aether_channel_subscription_delta
               WHERE
                 created_at > %s  AND
                 created_at <= %s AND
                 user_id = %s
               GROUP BY channel_id
               HAVING mod_sum != 0
               ORDER BY channel_id""", (start_time, end_time, user.id,)
        )

        item_deltas = request.connection.execute (
            """SELECT sum(mod_type) AS mod_sum, acid.item_id, acid.channel_id
                 FROM aether_channel_item_delta AS acid
               JOIN aether_channel_subscription AS acs ON acid.channel_id=acs.channel_id
                 WHERE
                   acid.channel_id IN (%s) AND
                   (acid.created_at > '%s' AND acid.created_at <= '%s') OR
                   (acs.created_at > '%s'  AND acs.created_at <= '%s')
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
                set_attribute (sub, 'action', 'removed')
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

@login_required
def register_client (request):
    #Stub
    
    try:
        c = Client ()

        c.user_id = request.user.id
        c.client_id = str (uuid4 ()).replace ('-', '')
        c.last_updated_ip = c.registration_ip = IP(request.META['REMOTE_ADDR']).int ()
        c.save (request.connection)

        ret = c.client_id
    except:
        ret = 'fail'
    
    return HttpResponse (ret)

def to_element (doc, name, val):
    node = doc.createElement (unicode (name))

    if val is not None:
        node.appendChild (doc.createTextNode (unicode (val)))

    return node

def set_attribute (node, name, val):
    if val is not None:
        node.setAttribute (unicode (name), unicode (val))