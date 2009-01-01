from channelguide import util
from channelguide.guide.models import Item
DEFAULT_WIDTH = 480
DEFAULT_HEIGHT= 360

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
""" % (DEFAULT_WIDTH, DEFAULT_HEIGHT + 15, item.url, item.url, DEFAULT_WIDTH,
       DEFAULT_HEIGHT + 15)

def flash_embed(item):
    return """<object width="%i" height="%i" codebase="http://download.macromedia.com/pub/shockwave/cabs/flash/swflash.cab#version=6,0,0,0" classid="clsid:D27CDB6E-AE6D-11cf-96B8-444553540000">
<param value="%s" name="movie"/>
<param value="true" name="allowfullscreen"/>
<param value="high" name="quality"/>
<param value="autoplay=1" name="FlashVars"/>
<param value="transparent" name="wmode"/>
<param value="video" name="id"/>
<embed id="video" width="%i" height="%i" allowfullscreen="true" type="application/x-shockwave-flash" pluginspage="http://www.macromedia.com/shockwave/download/index.cgi?P1_Prod_Version=ShockwaveFlash" wmode="transparent" quality="high" enablehref="false" flashvars="autoplay=1" src="%s\"/>
</object>""" % (DEFAULT_WIDTH, DEFAULT_HEIGHT + 36, item.url,
                DEFAULT_WIDTH, DEFAULT_HEIGHT + 36, item.url)

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
    'application/x-shockwave-flash': flash_embed,
    'video/x-flv': flash_embed,
    'video/flv': flash_embed,
}

def embed_code(item):
    func = EMBED_MAPPING.get(item.mime_type, default_embed)
    return func(item)

def item(request, id):
    item = util.get_object_or_404(request.connection,
                                  Item.query().join('channel'), id)
    previousSet = Item.query(Item.c.channel_id == item.channel_id,
                             Item.c.date < item.date).limit(1).order_by(
        Item.c.date, desc=True).execute(request.connection)
    if previousSet:
        previous = previousSet[0]
        print previous.date
    else:
        previous = None

    print item.date

    nextSet = Item.query(Item.c.channel_id == item.channel_id,
                         Item.c.date > item.date).limit(1).order_by(
        Item.c.date, ).execute(request.connection)
    if nextSet:
        next = nextSet[0]
        print next.date
    else:
        next = None
    return util.render_to_response(request, 'playback.html',
                                   {'item': item,
                                    'previous': previous,
                                    'next': next,
                                    'embed': util.mark_safe(embed_code(item)),
                                    })
