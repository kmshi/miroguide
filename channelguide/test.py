#!/usr/bin/env python2.4
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.remove(os.path.abspath(os.path.dirname(__file__)))
os.environ['DJANGO_SETTINGS_MODULE'] = 'channelguide.testsettings'

from unittest import TestLoader, TextTestRunner, TestSuite, TestCase
from optparse import OptionParser
import logging

from django.conf import settings
import django.test.utils
from channelguide import init
init.init_external_libraries()

class TestLogHandler(logging.Handler):
    def emit(self, record):
        if record.levelno >= logging.WARN:
            raise ValueError("got %s log record during tests" %
                    record.levelname)

def main(args):
    parse_args(args)
    logging.getLogger('').addHandler(TestLogHandler())
    setup_test_environment()
    try:
        tests = load_tests()
        runner = TextTestRunner()
        if options.verbose:
            runner.verbosity = 2
        runner.run(tests)
    finally:
        teardown_test_environment()

def parse_args(args):
    global options, parsed_args
    parser = OptionParser(usage="usage: %prog [options] [app1] [app2] ...")
    parser.add_option("-v", "--verbose", dest="verbose", action="store_true")
    (options, parsed_args) = parser.parse_args()

def setup_test_environment():
    global old_db_name
    old_db_name = settings.DATABASE_NAME
    django.test.utils.create_test_db()
    django.test.utils.setup_test_environment()
    from channelguide import db
    db.syncdb()

def teardown_test_environment():
    global old_db_name
    django.test.utils.teardown_test_environment()
    django.test.utils.destroy_test_db(old_db_name)

class OptionAwareTestLoader(TestSuite):
    def addTest(self, testCase):
        if isinstance(testCase, TestCase):
            test_id_parts = testCase.id().split(".")
            method = test_id_parts[-1]
            klass = test_id_parts[-2]
            module_name = testCase.__class__.__module__.split('.')[-1]
            for arg in parsed_args:
                if arg not in (method, klass, module_name):
                    return
        TestSuite.addTest(self, testCase)

test_packages = [
        'channelguide.guide.tests',
        'channelguide.newdb.tests',
]

def load_tests():
    loader = TestLoader()
    loader.suiteClass = OptionAwareTestLoader
    for package in test_packages:
        # forcing the improt now gives us better error messages sometimes
        __import__(package)
    tests = loader.loadTestsFromNames(test_packages)
    return tests

if __name__ == '__main__':
    main(sys.argv[1:])
