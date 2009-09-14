# Copyright (c) 2009 Michael C. Urbanski
# See LICENSE for details.

from IPy import IP
from uuid import uuid4
from time import mktime
from simplejson import dumps, loads
from datetime import datetime
from xml.dom.minidom import Document

from django.http import Http404, HttpResponse

from channelguide import sessions

from channelguide.guide.views.api import requires_login

from channelguide.guide.auth import login, login_required, SESSION_KEY
from channelguide.aether.dbutils import user_lock_required

from channelguide.guide.models.item import Item
from channelguide.guide.models.channel import Channel

from channelguide.aether.models import (
    ChannelSubscription, ChannelSubscriptionDelta,
    DownloadRequest, DownloadRequestDelta, Client
)

from channelguide.aether.forms import HashedPasswordLoginForm
from channelguide.aether.decorators import post_only

# Wishing the desktop client API were more like Last.FM's.  Will not require
# users to login on MG site when their session expires.

@post_only
def aether_authenticate (request):
    if request.method == 'POST':
        context = {}
        
        try:
            login_form = HashedPasswordLoginForm (
                request.connection, request.POST
            )

            if not login_form.is_valid ():
                context['message'] = 'Invalid username or password hash.'
                raise Exception ('Login invalid!')
            
            user = login_form.get_user ()
            sessionID = request.REQUEST.get ('session')

            if not sessionID:
                sessionID = sessions.util.make_new_session_key (
                    request.connection
                )

            session = sessions.util.get_session_from_key (
                request.connection, sessionID
            )

            data = session.get_data ()

            data['apiUser'] = user.id

            session.session_key = sessionID
            session.set_data (data)

            session.save (request.connection)

            context['status'] = 'success'
            context['session'] = sessionID
        except Exception as e:
            context['status'] = 'error'
    return HttpResponse (dumps (context), mimetype='application/json')

@post_only
@login_required
@user_lock_required
def queue_download (request, item_id):
    c = request.connection

    if not check_subscription (request.user, item_id, c):
        return HttpResponse (
            dumps ({ "status": "error" }), mimetype="application/json"
        )

    if not queued_for_download (request.user.id, item_id, c):
        DownloadRequest.insert (
            DownloadRequest (user=request.user, item_id=item_id),
            request.connection
        )

        DownloadRequestDelta.insert (
            DownloadRequestDelta (user=request.user, item_id=item_id),
            request.connection
        )

    return HttpResponse (
        dumps ({ "status": "queued" }), mimetype="application/json"
    )

@post_only
@login_required
@user_lock_required
def cancel_download (request, item_id):
    if not check_subscription (request.user, item_id, request.connection):
        return HttpResponse (
            dumps ({ "status": "error" }), mimetype="application/json"
        )
        
    if queued_for_download (request.user.id, item_id, request.connection):
        DownloadRequest.bulk_delete (
            user_id=request.user.id, item_id=item_id
        ).execute (request.connection)

        DownloadRequestDelta.insert (
            DownloadRequestDelta (user=request.user, item_id=item_id, mod_type=-1),
            request.connection
        )

    return HttpResponse (
        dumps ({ "status": "unqueued" }), mimetype="application/json"
    )
    
@post_only
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

    return HttpResponse (
        dumps ({ "status": "unsubscribed" }), mimetype="application/json"
    )

@post_only
@requires_login
@user_lock_required
def api_unsubscribe (request):
    context = {}
    try:
        json_request = loads (request.REQUEST['channels'])
        channel_ids = [int(id) for id in json_request['channels']]

        c = request.connection

        channel_ids = subscribed_from (request.user.id, channel_ids, c)
        
        if len (channel_ids) > 0:
            ChannelSubscription.bulk_delete (
                ChannelSubscription.c.channel_id.in_(channel_ids),
                user_id=request.user.id
            ).execute (c)

            for cid in channel_ids:
                ChannelSubscriptionDelta.insert (
                    ChannelSubscriptionDelta (
                        user_id=request.user.id, channel_id=cid, mod_type=-1
                    ), c
                )

        context = { "status": "success" }
        context = { "unsubscribed": channel_ids }
    except Exception, e:
        print 'Fuck Yeah Error Handling!  %s' % (e)
        context = { "status": "error" }
    return HttpResponse (
        dumps (context), mimetype="application/json"
    )

@post_only
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

    return HttpResponse (
        dumps ({ "status": "subscribed" }), mimetype="application/json"
    )
    
def check_subscription (user, item_id, conn):
    try:
        #Lazy way to generate a LookupError if the item doesn't exist, FIX ME.
        item = Item.get (conn, item_id)
    except Exception as e:
        if isinstance (e, LookupError):
            raise Http404 ()
        else:
            raise

    return subscribed (user.id, item.channel_id, conn)

def queued_for_download (user_id, item_id, conn):
    query = DownloadRequest.query ().where (user_id=user_id, item_id=item_id)

    if query.count (conn):
        return True

    return False

def subscribed (user_id, channel_id, conn):
    query = ChannelSubscription.query ().where (user_id=user_id, channel_id=channel_id)
    
    if query.count (conn):
        return True

    return False

def subscribed_from (user_id, channel_ids, conn):
    results = ChannelSubscription.query ().where (
         ChannelSubscription.c.channel_id.in_ (channel_ids), user_id=user_id
    ).execute (conn)

    return [c.channel_id for c in results]

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
    'feed_modified',
    'description',
    'license',
    'publisher',
    'url',
    'website_url'
]

@requires_login
@user_lock_required
def get_user_deltas (request):
#    for i in xrange(100000):
#        print i
    user = request.user
    
    try:
        client = Client.query (
            user_id=user.id, client_id=request.REQUEST['clientid']
        ).get (request.connection)

        time = float (request.REQUEST['since'])
        if time < 1:
            raise Exception ()
    except:
        raise Http404 ()

    end_time = datetime.now ()
    start_time = datetime.fromtimestamp (time)
    
#    start_time = client.last_updated
    
    if end_time < start_time:
        raise Http404 ()

    user.join ('subscriptions').execute (request.connection)

    sub_deltas = []
    item_deltas = []

    sub_ids = [s.channel_id for s in user.subscriptions]

    d = Document ()

    root = d.createElement('aether')
    set_attribute (root, 'updated', unicode (mktime(end_time.timetuple ())))

    d.appendChild (root)

    sub_deltas = request.connection.execute (
        """SELECT SUM(mod_type) AS mod_sum, channel_id
             FROM aether_channel_subscription_delta
           WHERE
             created_at > %s  AND
             created_at <= %s AND
             user_id = %s
           GROUP BY channel_id
           HAVING mod_sum != 0
           ORDER BY channel_id""", (start_time, end_time, user.id,)
    )

    if sub_deltas:
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
                    to_element (d, 'thumb_url', s.thumb_url_48_48 ())
                )

                channels.appendChild (sub)

        root.appendChild (channels)
    
    if (len (sub_ids)):
        item_deltas = request.connection.execute (
            """SELECT SUM(mod_type) AS mod_sum, acid.item_id, acid.channel_id
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
        print """SELECT SUM(adrd.mod_type) as mod_sum, adrd.item_id, acs.channel_id
                 FROM aether_download_request_delta AS adrd
               JOIN aether_channel_subscription AS acs ON
                    adrd.item_id = acs.channel_id
                 WHERE acs.channel_id IN (%s) AND adrd.user_id = %s AND
                   (adrd.created_at > '%s' AND adrd.created_at <= '%s') OR
                   (acs.created_at > '%s'  AND acs.created_at <= '%s')
               GROUP BY adrd.item_id
               HAVING mod_sum != 0
               ORDER BY adrd.item_id""" % (
                ','.join ([str(s) for s in sub_ids]),
                user.id, start_time, end_time, start_time, end_time
            )
        download_deltas = request.connection.execute (
            """SELECT SUM(adrd.mod_type) as mod_sum, adrd.item_id
                 FROM aether_download_request_delta AS adrd
               JOIN cg_channel_item AS cci ON
                 adrd.item_id = cci.id
               JOIN aether_channel_subscription AS acs ON
                 cci.channel_id = acs.channel_id
                 WHERE acs.channel_id IN (%s) AND adrd.user_id = %s AND
                   (adrd.created_at > '%s' AND adrd.created_at <= '%s') OR
                   (acs.created_at > '%s'  AND acs.created_at <= '%s')
               GROUP BY adrd.item_id
               HAVING mod_sum != 0
               ORDER BY adrd.item_id"""
            % (
                ','.join ([str(s) for s in sub_ids]),
                user.id, start_time, end_time, start_time, end_time
            )
        )

        if download_deltas:
            downloads = d.createElement ('downloads')

            for di in download_deltas:
                dr = d.createElement ('download')

                if di[0] > 0:
                    dr.setAttribute ('action', 'added')
                else:
                    dr.setAttribute ('action', 'removed')
                
                dr.appendChild (to_element (d, 'id', di[1]))
                downloads.appendChild (dr)

            root.appendChild (downloads)

    return HttpResponse(d.toxml (), mimetype='application/xml')

@requires_login
def register_client (request):
    #Stub
    try:
        c = Client ()

        c.user_id = request.user.id
        c.client_id = str (uuid4 ()).replace ('-', '')
        c.last_updated_ip = c.registration_ip = IP(request.META['REMOTE_ADDR']).int ()
        c.save (request.connection)

        ret = { 'status' : 'success', 'clientid': c.client_id }
    except:
        ret = { 'status': 'error' }

    return HttpResponse (
        dumps (ret), mimetype="application/json"
    )

    return HttpResponse (ret)

def to_element (doc, name, val):
    node = doc.createElement (unicode (name))

    if val is not None:
        node.appendChild (doc.createTextNode (unicode (val)))

    return node

def set_attribute (node, name, val):
    if val is not None:
        node.setAttribute (unicode (name), unicode (val))