#!/usr/bin/env python

import os
import sys

sys.path.append(os.path.abspath(os.path.join(".", "benchtester")))

AreWeSlimYetTests = {
  "Slimtest-Talos2.1-Standalone":
  {
    'type': "EnduranceTest",
    'vars':
      {
        'test': [ 'reserved', 'slimtest' ],
        'entities': 21,
        'iterations': 5,
        'delay': 0
      }
  }
};

# Load
import BenchTester
tester = BenchTester.BenchTester()

# Load modules for tests we have
for test in AreWeSlimYetTests.values():
  if not tester.load_module(test['type']):
    sys.exit(1)

# Parse command line arguments
args = tester.parse_args(sys.argv[1:])
if not args or not tester.setup(args):
  sys.exit(1)

# Run tests
for testname, testinfo in AreWeSlimYetTests.items():
  if not tester.run_test(testname, testinfo['type'], testinfo['vars']):
    sys.stderr.write("SlimTest: Failed at test %s\n" % testname)
    sys.exit(1)
