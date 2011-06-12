#!/usr/bin/env python
from django.core.management import execute_manager
import os, sys

sys.path.insert(0, os.path.join(os.path.abspath(os.path.dirname(__file__)), 'lib'))

try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)


# Pydev's MS-DOS Style path here can not work well with Cygwin POSIX Style path?

#if os.name != 'posix':
#    sys.path.append(os.path.join(settings.ROOT_DIR,'..','..',"eclipse-pydev\dropins\plugins\org.python.pydev.debug_1.6.5.2011020317\pysrc"))
#    import pydevd
#    pydevd.settrace()

if __name__ == "__main__":
    execute_manager(settings)
