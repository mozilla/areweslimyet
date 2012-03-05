#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2012 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys
import datetime

sys.path.append(os.path.abspath("benchtester"))
import BuildGetter
import BenchTester

AreWeSlimYetTests = {
  "Slimtest-TalosTP5":
  {
    'type': "EnduranceTest",
    'vars':
      {
        'test': [ 'mozmill_endurance_test' ],
        'entities': 100,
        'iterations': 5,
        'delay': 0
      }
  },
  "Slimtest-TalosTP5-Slow":
  {
    'type': "EnduranceTest",
    'vars':
      {
        'test': [ 'mozmill_endurance_test' ],
        'entities': 100,
        'iterations': 5,
        'delay': 0,
        'perTabPause': 10
      }
  },
};

##
## Main/command line
##

def stat(msg=""):
  sys.stderr.write("%s\n" % msg)
def usage():
  # TODO implement autobuild
  stat("Usage: %s { nightly | tinderbox } { build | [ startbuild | stopbuild ] }" % sys.argv[0])
  stat("\tFor nightly, builds are of format YYYY-MM-DD. Specifying a range builds one\n\t  per day for that date range (inclusive)")
  stat("\tFor tinderbox, builds are timestamps. Specifying a range builds all builds\n\t  inside that date range on FTP.m.o")
  sys.exit(1)
if len(sys.argv) < 3 or len(sys.argv) > 4:
  usage()

def parse_nightly_time(string):
  string = string.split('-')
  if (len(string) != 3):
    raise Exception("Could not parse %s as a YYYY-MM-DD date")
  return datetime.date(int(string[0]), int(string[1]), int(string[2]))
  
mode = sys.argv[1]
dorange = len(sys.argv) >= 4
# Queue builds
builds = []
if mode == 'nightly':
  startdate = parse_nightly_time(sys.argv[2])
  if dorange:
    enddate = parse_nightly_time(sys.argv[3])
    dates = range(startdate.toordinal(), enddate.toordinal() + 1)
  else:
    dates = [ startdate.toordinal() ]
  for x in dates:
    builds.append(BuildGetter.NightlyBuild(datetime.date.fromordinal(x)))
elif mode == 'tinderbox':
  startdate = float(sys.argv[2])
  if dorange:
    enddate = float(sys.argv[3])
    builds = BuildGetter.get_tinderbox_builds(startdate, enddate)
  else:
    builds.append(BuildGetter.TinderboxBuild(startdate))
else:
  raise Exception("Unknown mode %s" % mode)

print("Testing %u builds")

# Load
for build in builds:
  tester = BenchTester.BenchTester()

  # Load modules for tests we have
  for test in AreWeSlimYetTests.values():
    if not tester.load_module(test['type']):
      sys.exit(1)

  # Prepare build
  build.prepare()
  
  # Setup tester
  tester.setup({
    'buildname': build.get_revision(),
    'binary': build.get_binary(),
    'buildtime': build.get_buildtime(),
    'sqlitedb': "slimtest.sqlite",
    'logfile': "slimtest.log"
  })
  
  # Run tests
  for testname, testinfo in AreWeSlimYetTests.items():
    if not tester.run_test(testname, testinfo['type'], testinfo['vars']):
      sys.stderr.write("SlimTest: Failed at test %s\n" % testname)
      sys.exit(1)
  
  build.cleanup()
