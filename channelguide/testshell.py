#!/usr/bin/env python
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.remove(os.path.abspath(os.path.dirname(__file__)))
os.environ['DJANGO_SETTINGS_MODULE'] = 'channelguide.testsettings'
from django.conf import settings
from django.core.management import run_shell, setup_environ

from channelguide import testframework

def run_test_shell(use_plain=False):
    import django.test.utils
    old_db_name = settings.DATABASE_NAME
    django.test.utils.create_test_db()
    testframework.create_tables()
    run_shell(use_plain)
    django.test.utils.destroy_test_db(old_db_name)

if __name__ == "__main__":
    run_test_shell()
