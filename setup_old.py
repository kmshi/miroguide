#!/usr/bin/env python
# Run this to check/setup the correct permissions for the channelguide.

from os import chmod, stat, mkdir
from os.path import dirname, join, exists, abspath, isdir
from stat import *
import sys
import subprocess
import textwrap

base_dir = abspath(dirname(__file__))
static_dir = join(base_dir, 'static')
media_dir = join(static_dir, 'media')

saw_error = False

def check_writeable_dir(dir):
    global saw_error
    if not exists(dir):
        print "%s doesn't exist, creating it." % dir
        mkdir(dir)
    elif not isdir(dir):
        print "ERROR: %s exists but isn't a directory!  Exiting"
        saw_error = True
    perms = stat(dir)[ST_MODE]
    if not perms & 0006:
        print "setting a+w permission for %s" % dir
        chmod(dir, perms | 0006)

def check_import(module_name, package_name):
    global saw_error
    try:
        __import__(module_name)
    except ImportError:
        print "Error importing %s.  Make sure you install the %s package." % \
            (module_name, package_name)
        saw_error = True

def main(args):
    global saw_error
    check_writeable_dir(media_dir)
    check_import('MySQLdb', "MySQLdb")
    try:
        subprocess.Popen(["identify"], stdout=subprocess.PIPE).communicate()
        subprocess.Popen(["convert"], stdout=subprocess.PIPE).communicate()
    except OSError:
        print "ImageMagick doesn't seem to be installed"
        saw_error = True

    if saw_error:
        sys.exit(1)
    else:
        output = ('Dependencies look okay.  '
                'Make sure %s is writable by the apache user' % media_dir)
        for line in textwrap.wrap(output, 78):
            print line

if __name__ == '__main__':
    main(sys.argv)
