from fabric.api import *
env.hosts = ['pcf8.pculture.org'] # credentials setup in .ssh/config

REQUIREMENTS = 'http://git.participatoryculture.org/miroguide/plain/requirements.txt'

def update(dir_='miroguide.dev'):
    with cd('/var/www/%s/' % dir_):
        run("yes i|pip -E . install -r '%s'" % REQUIREMENTS)
        if dir_ == 'miroguide':
            with cd('src/guide/static'):
                for static_dir in ['css', 'images', 'js', 'movies',
                                   'swf']:
                    run('~/s3sync/s3sync.rb -r -p '
                        '%s/ s3.miroguide.com:static/%s/' % (
                            static_dir, static_dir))
        sudo('touch project/apache/dispatch.wsgi')
