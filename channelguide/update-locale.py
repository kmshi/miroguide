import sys
import os, os.path
filename = sys.argv[1]
import tarfile
tf = tarfile.open(filename)

info = tf.next()
while info is not None:
    if info.name.endswith(".po"):
        lang = info.name[12:-3]
        extractPath = 'locale/%s/LC_MESSAGES/django.po' % lang
        try:
            os.makedirs(os.path.dirname(extractPath))
        except OSError, e:
            if e.errno != 17: # file exists
                raise
        print 'extracting %s to %s' % (info.name, extractPath)
        open(extractPath, 'w').write(tf.extractfile(info).read())
    info = tf.next()
