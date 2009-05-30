/* 
 * Copyright (c) 2009 Michael C. Urbanski
 * See LICENSE for details.
 */
var aether_queue_url   = '/aether/queue/';
var aether_dequeue_url = '/aether/dequeue/';

function queue_download (id)
{
    handle_download_request (id, true)
}

function dequeue_download (id)
{
    handle_download_request (id, false)
}

function handle_download_request (id, queue)
{
    var url = queue ? aether_queue_url : aether_dequeue_url ;

    $.ajax ({
      type: 'POST',
      datatype: 'json',
      url: url+id,

      success: function (data, status) {
        ret = jeval (data);        
        update_item (id, ret.status);
      },

      failure: function (msg) {
        update_item (id, 'error');
      }
    });
}

function update_item (id, status)
{
    var cls;
    var queued;
    var item = $('#aether_item_' + id);
    
    switch (status) {
    case 'unqueued':
        cls = 'aqd';
        queued = false;
        break;

    case 'error':
    case 'queued':
        cls = 'aqc';
        queued = true;
        break;
    }
    
    item.removeClass ();
    
    // This should be fine as long as there is only one onclick method.
    // The alternatives sucked even more.  Let me know if you know of a better way/
    document.getElementById ('aether_item_'+id).onclick = function () {
        if (queued) {
            dequeue_download (id);
        } else {
            queue_download (id)
        }
    }

    item.addClass (cls);
}

function jeval (json)
{
    return eval('(' + json + ')');
}