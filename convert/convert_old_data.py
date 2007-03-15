import os
cg_basedir = os.path.abspath(os.path.join(__file__, '..', '..'))
import sys
sys.path.append(os.path.abspath(os.path.join(cg_basedir, '..')))
os.environ['DJANGO_SETTINGS_MODULE'] = 'channelguide.settings'

import itertools

from django.conf import settings
from sqlalchemy import Table, select, func, create_session, eagerload

from channelguide import util

def get_mysql_args(use_db_name=True):
    args = ''
    if use_db_name:
        args += settings.DATABASE_NAME
    if settings.DATABASE_USER:
        args += " -u %s" % settings.DATABASE_USER
    if settings.DATABASE_PASSWORD:
        args += ' --password=%s' % settings.DATABASE_PASSWORD
    if settings.DATABASE_HOST:
        args += ' -h %s' % settings.DATABASE_HOST
    if settings.DATABASE_PORT:
        args += ' -P %s' % settings.DATABASE_PORT
    return args

def execute_sql_file(sql_path):
    cmd = 'mysql %s < %s' % (get_mysql_args(), sql_path)
    os.system(cmd)

def execute_convert_sql_file(convert_name):
    sql_path = os.path.join(cg_basedir, 'convert', convert_name)
    execute_sql_file(sql_path)

def execute_sql(sql, use_db_name=True):
    cmd = 'mysql %s -e "%s"' % (get_mysql_args(use_db_name), sql)
    os.system(cmd)

def drop_table(table):
    execute_sql("DROP TABLE %s" % table)

def drop_tables(*tables):
    for t in tables:
        drop_table(t)

def fix_utf8():
    from channelguide import db
    from channelguide.channels.models import Channel
    connection = db.connect()
    session = create_session(bind_to=connection)
    query = session.query(Channel).options(eagerload('items'))
    pprinter = util.ProgressPrinter("fixing utf8 data", query.count())
    count = itertools.count()
    for channel in query.select():
        channel.fix_utf8_strings()
        if count.next() % 100 == 0:
            session.flush()
        pprinter.iteration_done()
    session.flush()
    pprinter.loop_done()

def convert_thumbnails():
    from channelguide import db
    from channelguide.channels.models import Channel
    connection = db.connect()
    # calculate what to download
    to_download = {}
    local_files = {}
    pculture_url = 'https://channelguide.participatoryculture.org/'
    file_table = Table('files', db.metadata, autoload=True)
    file_select = select([file_table.c.nid, file_table.c.filepath])
    for row in connection.execute(file_select):
        if os.path.exists(row['filepath']):
            local_files[row['nid']] = row['filepath']
        else:
            to_download[row['nid']] = pculture_url + row['filepath']
    # download images
    image_data = dict(util.grab_urls(to_download.values()))
    # store the images
    session = create_session(bind_to=connection)
    pprinter = util.ProgressPrinter("storing thumbnails", 
            len(to_download) + len(local_files))
    def save_thumbnail(id, data):
        channel = session.get(Channel, nid)
        if channel is not None:
            try:
                channel.save_thumbnail(data)
            except Exception, e:
                print
                print "Error saving thumbnail for %s (%s)" % (id, e)

    for nid, url in to_download.items():
        this_image_data = image_data[url]
        if not isinstance(this_image_data, Exception):
            save_thumbnail(nid, this_image_data)
        pprinter.iteration_done()
    for nid, path in local_files.items():
        save_thumbnail(nid, util.read_file(path))
        pprinter.iteration_done()
    pprinter.loop_done()

def main():
    execute_sql("DROP DATABASE channelguide", use_db_name=False)
    execute_sql("CREATE DATABASE channelguide", use_db_name=False)
    os.system("python %s syncdb" % (os.path.join(cg_basedir, 'manage.py')))
    print "loading channelguide data"
    execute_sql_file('cg.sql')
    print "converting channelguide data"
    execute_convert_sql_file('convert_cg.sql')
    print "converting thumbnails"
    if '--no-utf8-fix' not in sys.argv:
        fix_utf8()
    if '--no-thumbs' not in sys.argv:
        convert_thumbnails()
    drop_tables('channel_categories', 'channel_featured', 'channel_info',
            'channel_languages', 'channel_tags', 'node', 'tags', 'users', 
            'files', 'users_roles')
    print "loading videobomb data"
    execute_sql_file('vb.sql')
    print "converting videobomb data"
    execute_convert_sql_file('convert_vb.sql')
    drop_tables('user_cache', 'user_auth_hashes', 'users')

if __name__ == '__main__':
    main()
