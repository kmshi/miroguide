#!/bin/sh
echo "stopping apache"
/etc/init.d/httpd stop
echo "updating from SVN"
svn up
echo "updating database"
python channelguide/manage.py syncdb
echo "optimizing templates"
python channelguide/manage.py optimize_templates
echo "clearing the cache"
python channelguide/manage.py clear_cache
echo "starting apache"
/etc/init.d/httpd restart
echo "all systems go"
