/* share.js
 * 
 * Stuff for sharing videos, feeds
 */

function submit_share(data, text_status) {
    $('#share_div').empty().append(data);
    $('#share_form').ajaxForm(submit_share);
}

function add_share_callback() {
    $('#share_form').ajaxForm(submit_share);
}