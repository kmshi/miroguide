#!/usr/bin/env python2.4

def startup():
    import os
    import sys
    channelguide_dir = os.path.dirname(__file__)
    sys.path.insert(0, os.path.abspath(os.path.join(channelguide_dir, '..')))
    for i in reversed(range(len(sys.path))):
        if (os.path.isdir(sys.path[i]) and 
                os.path.samefile(sys.path[i], channelguide_dir)):
            del sys.path[i]
    os.environ['DJANGO_SETTINGS_MODULE'] = 'channelguide.settings'
    from channelguide import init
    init.initialize()

    from flup.server.fcgi import WSGIServer
    from django.core.handlers.wsgi import WSGIHandler
    from django.conf import settings
    WSGIServer(WSGIHandler(), maxThreads=settings.MAX_THREADS).run()


if __name__ == '__main__':
    startup()
