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
    download = item.children('a.download');
    mimetype = download.text();
    if (supportsMimeType(mimetype)) {
        item.addClass('playable').children('.thumb img').click(playVideo);
    }
}

function playVideo() {
    item = $(this).parent('.details');
    download = item.children('a.download');
    url = download.attr('href');
    console.log(url);
    embed = $('<embed class="thumb" width="154" height="105"/>');
    embed.attr('src', url);
    item.children('.thumb').replaceWith(embed);
}