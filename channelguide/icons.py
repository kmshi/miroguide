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
    make_icons_big_on_featured()
    make_icons_big_on_blue()
    make_icons_small_on_silver()

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

def make_icons_small_on_silver():
    make_icons_on_color(small_icons.items(), 'silver', '#dbdbdb')

def make_icons_big_on_blue():
    make_icons_on_color(big_icons.items(), 'blue', '#333355')

def make_icons_big_on_featured():
    for name, size in big_icons.items():
        if 'add' in name:
            offset = 23
        else:
            offset = 81
        source = source_path(name)
        dest = dest_path(name, 'feature')
        print os.path.basename(dest)
        bg = os.path.join(image_dir, 'featured-bg.png')
        # get the source gradient
        cmd('convert', bg,
                '-crop', '1x%d+0+%d' % (size, offset),
                '+repage',
                dest)
        # widen it and make it big enough for the normal + hover image
        cmd('convert',
                '-size', '%dx%d' % (size, size*2),
                'tile:%s' % dest, dest)
        compose(source, dest)
