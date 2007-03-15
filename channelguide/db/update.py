import glob
import logging
import os
import re

from version import get_version, set_version
from channelguide import util

def find_updates(update_dir):
    all_files = glob.glob(os.path.join(update_dir, '*.py'))
    all_files += glob.glob(os.path.join(update_dir, '*.sql'))
    scripts = {}
    for path in all_files:
        m = re.match(r'(\d+)_.*', os.path.basename(path))
        if m:
            scripts[int(m.group(1))] = path
    return scripts

def execute_sql_file(connection, file):
    splitter = re.compile(r';[ \t]*$', re.M)
    for statement in splitter.split(util.read_file(file)):
        # remove comments
        statement = re.sub(r"--.*[\n\Z]", "", statement)
        statement = statement.strip()
        if statement:
            results = connection.execute(statement)

def execute_updates(connection, scripts):
    version = get_version(connection)
    while version + 1 in scripts:
        script = os.path.normpath(scripts[version+1])
        logging.info("running update %d: %s" % (version+1, script))
        if script.endswith(".py"):
            globals = {'connection': connection}
            execfile(script, globals, {})
        elif script.endswith(".sql"):
            execute_sql_file(connection, script)
        else:
            raise ValueError("don't know how to execute update script %s" %
                    script)
        version += 1
        set_version(connection, version)

def run_updates(connection, update_dir):
    scripts = find_updates(update_dir)
    execute_updates(connection, scripts)
