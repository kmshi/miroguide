#!/usr/bin/env python2.4

# sqlhelper -- SQL helper tools
# Copyright (C) 2005-2007 Participatory Culture Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

from unittest import TestLoader, TextTestRunner, TestSuite, TestCase
from optparse import OptionParser
import os
import sys
import time

def main(args):
    fix_path()
    import testsetup
    parse_args(args)
    tests = load_tests()
    runner = TextTestRunner()
    if options.verbose:
        runner.verbosity = 2
    try:
        # clear out old test databases if they're around
        testsetup.dbinfo.drop_database()
    except:
        pass
    testsetup.dbinfo.create_database()
    try:
        runner.run(tests)
    finally:
        print "droping test database (this make take a little while...)"
        for x in range(5):
            try:
                testsetup.dbinfo.drop_database()
            except:
                time.sleep(1)
            else:
                break

def fix_path():
    try:
        import sqlhelper
    except:
        up_one_level = os.path.abspath(os.path.join(__file__, '..', '..'))
        sys.path.append(up_one_level)

def parse_args(args):
    global options, parsed_args
    parser = OptionParser(usage="usage: %prog [options] [testname] [testname2] ...")
    parser.add_option("-v", "--verbose", dest="verbose", action="store_true")
    (options, parsed_args) = parser.parse_args()

class OptionAwareTestLoader(TestSuite):
    def addTest(self, testCase):
        if isinstance(testCase, TestCase):
            test_id_parts = testCase.id().split(".")
            method = test_id_parts[-1]
            klass = test_id_parts[-2]
            module_name = testCase.__class__.__module__.split('.')[-1]
            package_name = testCase.__class__.__module__.split('.')[-3]
            for arg in parsed_args:
                if arg not in (method, klass, module_name, package_name):
                    return
        TestSuite.addTest(self, testCase)

def load_tests():
    loader = TestLoader()
    loader.suiteClass = OptionAwareTestLoader
    # import the test package now, if an import fails we get a better error
    # message than if it fails in loadTestsFromNames
    import sqlhelper.tests 
    tests = loader.loadTestsFromNames(['sqlhelper.tests'])
    return tests

if __name__ == '__main__':
    main(sys.argv[1:])
