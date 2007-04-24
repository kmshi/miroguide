#!/usr/bin/env python
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
    parser.add_option("-m", "--method", dest="method",
                      help="test case method name", metavar="METHOD")
    parser.add_option("-c", "--class", dest="klass",
                      help="test case class name", metavar="CLASS")
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
            if options.klass is not None and klass != options.klass:
                return
            if options.method is not None and method != options.method:
                return
        TestSuite.addTest(self, testCase)

def load_tests():
    loader = TestLoader()
    loader.suiteClass = OptionAwareTestLoader
    if parsed_args:
        names = ['channelguide.guide.tests.%s' % mod for mod in parsed_args]
    else:
        names = ['channelguide.guide.tests']
    # if there's an import error, loadTestsFromNames doesn't give a good
    # traceback, force the issue here.
    for name in names:
        __import__(name)
    tests = loader.loadTestsFromNames(names)
    return tests

if __name__ == '__main__':
    main(sys.argv[1:])
