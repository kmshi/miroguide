#!/bin/sh
#echo "updating from SVN"
#svn up
echo "updating database"
python channelguide/manage.py syncdb
echo "optimizing templates"
python channelguide/manage.py optimize_templates
echo "clearing the cache"
python channelguide/manage.py clear_cache
echo "restarting server"
touch channelguide/dispatch.fcgi
echo "all systems go"
