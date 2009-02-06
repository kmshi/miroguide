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
    videoItem = $(this);
    download = videoItem.children('a.playback');
    mimetype = download.text();
    if (supportsMimeType(mimetype)) {
        videoItem.children('.thumb').prepend('<div class="play_vid_overlay"></div>').parent().find('span.thumb').css('cursor', 'pointer').click(playVideo);
    }
}

function playVideo() {
    if ($("#channelEpisodes .thumb .hd_tag_small").length) {
        if (!confirm('Are you sure you want to stream this High-Definition video?'))
            return;
    }
    videoItem = $(this).parent('.details');
    download = videoItem.children('a.playback');
    location.href = download.attr('href');
}