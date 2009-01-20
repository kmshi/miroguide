/* share.js
 * 
 * Stuff for sharing videos, feeds
 */

function submit_share(data, text_status) {
    $('#share_div').empty().append(data);
    $('#share_form').ajaxForm(submit_share);
}

function hide_share_box() {
    $('#share_box').css('display', 'none');
}

function add_share_callbacks() {
    $('#share_form').ajaxForm(submit_share);
    $('#share_close').bind('click', hide_share_box);
}