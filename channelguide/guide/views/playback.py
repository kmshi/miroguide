from channelguide import util
from channelguide.guide.models import Item
DEFAULT_WIDTH = 480
DEFAULT_HEIGHT= 375

def quicktime_embed(item):
    return """<object id="video" classid="clsid:02BF25D5-8C17-4B23-BC80-D3488ABDDC6B" width="%i" height="%i" bgcolor="ffffff" codebase="http://www.apple.com/qtactivex/qtplugin.cab">
<param name="src" value="%s">
<param name="scale" value="aspect">
<param name="id" value="video">
<param name="autoplay" value="true">
<param name="controller" value="true">
<embed src="%s" bgcolor="ffffff" name="movieobject" scale="aspect" width="%i" height="%i" id="video" autoplay="true" controller="true" pluginspage="http://www.apple.com/quicktime/download/">
</embed>
</object>
""" % (DEFAULT_WIDTH, DEFAULT_HEIGHT, item.url, item.url, DEFAULT_WIDTH,
       DEFAULT_HEIGHT)

def default_embed(item):
    return """<embed width="%i" height="%i" src="%s"></embed>""" % (
        DEFAULT_WIDTH, DEFAULT_HEIGHT, item.url)

EMBED_MAPPING = {
    'video/mp4': quicktime_embed,
    'video/quicktime': quicktime_embed,
    'audio/mpeg': quicktime_embed,
    'video/x-m4v': quicktime_embed,
    'video/mpeg': quicktime_embed,
    'video/m4v': quicktime_embed,
    'video/mov': quicktime_embed,
    'audio/x-m4a': quicktime_embed,
    'audio/mp4': quicktime_embed,
    'video/x-mp4': quicktime_embed,
    'audio/mp3': quicktime_embed,
}

def embed_code(item):
    func = EMBED_MAPPING.get(item.mime_type, default_embed)
    return func(item)

def item(request, id):
    item = util.get_object_or_404(request.connection,
                                  Item.query().join('channel'), id)
    return util.render_to_response(request, 'playback.html',
                                   {'item': item,
                                    'embed': util.mark_safe(embed_code(item)),
                                    })

