"""Tools for getting data from feedparser objects.  Most of this code is
ripped out from democracy.
"""

def get_first_video_enclosure(entry):
    """Find the first video enclosure in a feedparser entry.  Returns the
    enclosure, or None if no video enclosure is found.
    """

    try:
        enclosures = entry.enclosures
    except (KeyError, AttributeError):
        return None
    for enclosure in enclosures:
        if has_video_type(enclosure):
            return enclosure
    return None

def has_video_type(enclosure):
    try:
        type = enclosure['type']
    except KeyError:
        return False
    application_video_mime_types = [
        "application/ogg", 
        "application/x-annodex",
        "application/x-bittorrent", 
        "application/x-shockwave-flash"
    ]
    return (type.startswith('video/') or type.startswith('audio/') or
            type in application_video_mime_types)

def get_thumbnail_url(entry):
    """Get the URL for a thumbnail from a feedparser entry."""
    # Try the video enclosure
    video_enclosure = get_first_video_enclosure(entry)
    if video_enclosure is not None:
        try:
            return to_utf8(video_enclosure["thumbnail"]["url"])
        except KeyError:
            pass 
    # Try to get any enclosure thumbnail
    for enclosure in entry.enclosures:
        try:
            return to_utf8(enclosure["thumbnail"]["url"])
        except KeyError:
            pass
    # Try to get the thumbnail for our entry
    try:
        return to_utf8(entry["thumbnail"]["url"])
    except KeyError:
        return None

def to_utf8(feedparser_string):
    if str is None:
        return None
    elif type(feedparser_string) is str:
        return feedparser_string.decode('utf-8', 'replace').encode('utf-8')
    else:
        return feedparser_string.encode('utf-8')
