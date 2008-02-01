#!/usr/bin/env python

def startup():
    import os
    import sys
    import logging
    import traceback
    channelguide_dir = os.path.dirname(__file__)
    start_mtime = os.stat(__file__).st_mtime
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
    class CGServer(WSGIServer):
        def error(self, req):
            try:
                from channelguide.guide.views import errors
                page = errors.render_error_500(req)
            except:
                logging.warn("Error generating 500 error page!\n%s",
                        traceback.format_exc())
                page = '500 Error'
            req.stdout.write('HTTP/1.1 500 INTERNAL SERVER ERROR\r\n')
            req.stdout.write('Content-Type: text/html\r\n\r\n' + page)
        def _mainloopPeriodic(self):
            if os.stat(__file__).st_mtime > start_mtime:
                self._exit()
    CGServer(WSGIHandler(), maxThreads=settings.MAX_THREADS).run()

if __name__ == '__main__':
    startup()
