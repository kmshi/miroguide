function supportsMimeType(mimetype) {
    if (navigator.mimeTypes) {
        if (navigator.mimeTypes[mimetype]) {
            return navigator.mimeTypes[mimetype].enabledPlugin;
        } else {
            return false;
        }
    }
    if (navigator.plugins) {
        for (i=0; i<navigator.plugins.length; i++) {
            plugin = navigator.plugins[i];
            for (j=0; j < plugin.length; j++) {
                if (plugin[j].type == mimetype) {
                    return plugin;
                }
            }
        }
    }
    return false;
}

function setUpItem() {
    item = $(this);
    download = item.children('a.playback');
    mimetype = download.text();
    if (supportsMimeType(mimetype)) {
        item.children('.thumb').prepend('<div class="play_vid_overlay"></div>').parent().children('.thumb img').css('cursor', 'pointer').click(playVideo);
    }
}

function playVideo() {
    if ($("#channelDetails .thumb .channel_hd").length) {
        if (!confirm('Are you sure you want to stream this High-Definition video?'))
            return;
    }
    item = $(this).parent('.details');
    download = item.children('a.playback');
    location.href = download.attr('href');
}