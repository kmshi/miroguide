# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

import os

from django.conf import settings

from channelguide import util

image_dir = os.path.join(settings.STATIC_DIR, 'css', 'images')
icon_dir = os.path.join(image_dir, 'icons')
icon_source_dir = os.path.join(icon_dir, 'source')

# icons are stored a name -> size
big_icons = {
        'add-big': 24,
        'info-big': 24,
}

small_icons = {
        'add-small': 16,
        'info-small': 16,
}
icons = small_icons.copy()
icons.update(big_icons)

def source_path(name):
    return os.path.join(icon_source_dir, '%s.png' % name)

def dest_path(name, extra):
    return os.path.join(icon_dir, '%s-%s.png' % (name, extra))

def cmd(*args):
    util.call_command(*args)

def compose(source, dest):
    cmd('composite', 
            '-compose', 'src-over',
            source, dest, dest)

def make_icons():
    make_icons_big_on_white()
    make_icons_small_on_white()

def make_icons_on_color(icons, name_extra, color):
    for name, size in icons:
        source = source_path(name)
        dest = dest_path(name, name_extra)
        print os.path.basename(dest)
        cmd('convert',
                '-size', '%dx%d' % (size, size * 2),
                'xc:black', dest)
        cmd('convert', dest,
                '-fill', color,
                '-colorize', '100%',
                dest)
        compose(source, dest)

def make_icons_small_on_white():
    make_icons_on_color(small_icons.items(), 'white', '#fff')

def make_icons_big_on_white():
    make_icons_on_color(big_icons.items(), 'white', '#fff')

