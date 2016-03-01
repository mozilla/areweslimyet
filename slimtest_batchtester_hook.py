#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2012 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

# Lets you use BatchTester to batch-run the AWSY builds. The --status-file
# BatchTester can generate is what html/status/status.json is, and what
# html/status monitors
#
# python benchtester/BatchTester.py --hook slimtest_batchtester_hook <...>

import sys
import os
import subprocess
import sqlite3
import time
import datetime

execfile("slimtest_config.py")

sql = None

def database_for_build(build):
  if build.series:
    return os.path.join("db", "custom-%s-x.sqlite" % build.series)

  date = datetime.date.fromtimestamp(build.build.get_buildtime())
  return os.path.join("db", "areweslimyet-%04u-%02u.sqlite" % (date.year, date.month))

def stat(msg, logfile=None):
  msg = "%s :: %s\n" % (time.ctime(), msg)
  sys.stderr.write("[SlimTest] %s" % msg)
  if logfile:
    logfile.write(msg)
    logfile.flush()

def cli_hook(parser):
  parser.add_argument('--skip-existing', action='store_true', help="Check the sqlite database and skip a build if it already has complete test data")

def should_test(build, args):
  dbname = database_for_build(build)
  if os.path.exists("%s.xz" % (dbname,)):
    # Database is archived, don't create a duplicate
    build.note = "Test database for this build's month (%s) has been archived, refusing to test" % (dbname,)
    return False

  # No builds for this db yet
  if not os.path.exists("%s" % (dbname,)):
    return True

  try:
    sql = sqlite3.connect(dbname, timeout=900)
    sql.row_factory = sqlite3.Row
  except Exception, e:
    build.note = "Internal Error: Failed to open database for given month (%s)" % (dbname,)
    return False


  res = sql.execute("SELECT `id` FROM `benchtester_builds` WHERE `name` = ?", [build.revision])
  row = res.fetchone()
  if not row: return True

  res = sql.execute("SELECT `name` FROM `benchtester_tests` WHERE `successful` = 1 AND `build_id` = ?", [row['id']])
  have_tests = set(map(lambda x: x['name'], res.fetchall()))
  sql.close()
  for x in AreWeSlimYetTests:
    if not x in have_tests:
      return True

  build.note = "Build has complete test data"
  if build.force:
    build.note += ", but --force given. Testing anyway."
    stat("Force testing build with test data: %s" % (build.revision,))
    return True
  else:
    stat("Skipping build with test data: %s" % (build.revision,))
    return False

def run_tests(build, args):
  import BenchTester

  if args.get('logdir'):
    logfile = os.path.join(args.get('logdir'), "%s.test.log" % (build.revision,))
    gecko_logfile = os.path.join(args.get('logdir'), "%s.gecko.log" % (build.revision,))
  else:
    logfile = None
    gecko_logfile = None

  tester = BenchTester.BenchTester(logfile)
  # Load modules for tests we have
  for test in AreWeSlimYetTests.values():
    if not tester.load_module(test['type']):
      raise Exception("Could not load module %s" % (test['type'],))

  tester.setup({
    'buildname': build.revision,
    'binary': build.build.get_binary(),
    'buildtime': build.build.get_buildtime(),
    'sqlitedb': database_for_build(build),
    'logfile': logfile,
    'gecko_log': gecko_logfile,
    'marionette_port': 24242 + build.num # Use different marionette ports so as not to collide
  })

  display = ":%u" % (build.num + 9,)
  # kill this display if its already running for some reason
  try: subprocess.check_output([ "vncserver", "-kill", display ])
  except: pass

  # Start VNC display
  subprocess.check_output([ "vncserver", display ])
  os.environ['DISPLAY'] = display
  # Run tests
  try:
    for testname, testinfo in AreWeSlimYetTests.items():
      if not tester.run_test(testname, testinfo['type'], testinfo['vars']):
        raise Exception("SlimTest: Failed at test %s -- Errors: %s -- Warnings: %s\n" % (testname, tester.errors, tester.warnings))
  finally:
    subprocess.check_output([ "vncserver", "-kill", display ])

  if len(tester.errors):
    raise Exception("Build completed, but generated errors: %s" % (tester.errors,))
