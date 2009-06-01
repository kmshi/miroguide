/* 
 * Copyright (c) 2009 Michael C. Urbanski
 * See LICENSE for details.
 */

$(document).ready (function () {
    $('.aqd, .aqc').each (function (pos, item) {
        item = $(this);

        if (item.attr ('class') == 'aqd') {
            click_handler (item.attr ('id'), function () { queue_download (item.attr ('id')) });
        } else {
            click_handler (item.attr ('id'), function () { dequeue_download (item.attr ('id')) });
        }
    });
});

var aether_queue_url   = '/aether/queue/';
var aether_dequeue_url = '/aether/dequeue/';
var aether_subscribe_url   = '/aether/subscribe/';
var aether_unsubscribe_url = '/aether/unsubscribe/';

function subscribe (id)
{
    handle_subscription_request (id, true);
}

function unsubscribe (id)
{
    handle_subscription_request (id, false);
}

function handle_subscription_request (id, subscribe)
{
    var url = subscribe ? aether_subscribe_url : aether_unsubscribe_url ;
    //update_item (id, 'updating');

    $.ajax ({
      type: 'POST',
      datatype: 'json',
      url: url+(id.split ('_').slice (-1)),

      success: function (data, status) {
        ret = jeval (data);
        update_subscription (id, ret.status);
      },

      error: function (xhr, status, error) {
        //update_item (id, 'error');
      }
    });
}

function queue_download (id)
{
    handle_download_request (id, true);
}

function dequeue_download (id)
{
    handle_download_request (id, false);
}

function handle_download_request (id, queue)
{
    var url = queue ? aether_queue_url : aether_dequeue_url ;
    update_item (id, 'updating');

    $.ajax ({
      type: 'POST',
      datatype: 'json',
      url: url+(id.split ('_').slice (-1)),

      success: function (data, status) {
        ret = jeval (data);        
        update_item (id, ret.status);
      },

      error: function (xhr, status, error) {
        update_item (id, 'error');
      }
    });
}

function update_subscription (channel_id, status)
{
    var channel = $('#'+channel_id);

    if (status == 'subscribed') {
        subscribed = true;
        $('.uaqd, .uaqc').each (function (pos, item) {
            item = $(this);
            toggle_item_sensitivity (item);

            if (item.attr ('class') == 'aqd') {
                click_handler (item.attr ('id'), function () { queue_download (item.attr ('id')) });
            } else {
                click_handler (item.attr ('id'), function () { dequeue_download (item.attr ('id')) });
            }
        });
    } else {
        subscribed = false;
        $('.aqd, .aqc').each (function (pos, item) {
            item = $(this);
            toggle_item_sensitivity (item);
            click_handler (item.attr ('id'), null);
        });
    }

    // Not translated == teh suck.
    // This still needs work.
    if (subscribed) {
        channel.html ('<span>Unsubscribe</span>');
        click_handler (channel_id, function () { unsubscribe (channel_id) });
    } else {
        channel.html ('<span>Subscribe</span>');
        click_handler (channel_id, function () { subscribe (channel_id) });
    }
}

function update_item (item_id, status)
{
    var cls;
    var queued;
    var item = $('#' + item_id);
    
    switch (status) {

    case 'updating':
        cls = 'aqr';
        break;
    case 'unqueued':
        cls = 'aqd';
        queued = false;
        break;
    case 'queued':
        cls = 'aqc';
        queued = true;
        break;
    case 'error':
        cls = 'aqe';
        break;
    }

    item.attr ('class', cls);

    if (status == 'updating' || status == 'error') {
        return;
    }

    if (queued) {
        click_handler (item_id, function () { dequeue_download (item_id) });
    } else {
        click_handler (item_id, function () { queue_download (item_id) });
    }
}

function toggle_item_sensitivity (item)
{
    var cls = item.attr ('class');

    switch (cls) {
    case 'aqd':
        item.attr ('class', 'uaqd');
        break;
    case 'aqc':
        item.attr ('class', 'uaqc');
        break;
    case 'uaqd':
        item.attr ('class', 'aqd');
        break;
    case 'uaqc':
        item.attr ('class', 'aqc');
        break;
    }
}

function click_handler (i, f)
{
    document.getElementById (i).onclick = f;
}

function jeval (json)
{
    return eval('(' + json + ')');
}