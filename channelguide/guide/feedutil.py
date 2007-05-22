"""Tools for getting data from feedparser objects.  Most of this code is
ripped out from democracy.
"""

from datetime import datetime

from sqlhelper.orm import columns

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
        try:
            decoded = feedparser_string.decode('utf-8')
        except UnicodeError:
            try:
                decoded = feedparser_string.decode('latin-1')
            except UnicodeError:
                decoded = feedparser_string.decode('utf-8', 'ignore')
        return decoded.encode('utf-8')
    else:
        return feedparser_string.encode('utf-8')

string_column_cache = {}
def get_string_columns(obj):
    try:
        return string_column_cache[obj.__class__]
    except KeyError:
        cols = [c for c in obj.c if isinstance(c, columns.String)]
        string_column_cache[obj.__class__] = cols
        return cols

def fix_utf8_strings(obj):
    # cache string columns for fast access
    changed = False
    for c in get_string_columns(obj):
        org = obj.__dict__.get(c.name)
        if org is None:
            continue
        fixed = to_utf8(org)
        if org != fixed:
            changed = True
            setattr(obj, c.name, fixed)
    return changed

def struct_time_to_datetime(time):
    return datetime(*time[:6])
