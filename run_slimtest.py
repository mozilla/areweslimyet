#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2012 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys
import argparse
import time
import datetime
import multiprocessing

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
        'perTabPause': 0
      }
  },
};

parser = argparse.ArgumentParser(description='Run the areweslimyet.com tests against one or more builds in parallel')
parser.add_argument('--mode', help='nightly or tinderbox')
parser.add_argument('--batch', help='Batch mode -- given a folder name, treat each file within as containing a set of arguments to this script, deleting each file as it is processed.')
parser.add_argument('--firstbuild', help='For nightly, the date (YYYY-MM-DD) of the first build to test. For tinderbox, the timestamp to start testing builds at.')
parser.add_argument('--lastbuild', help='[optional] For nightly builds, the last date to test. For tinderbox, the timestamp to stop testing builds at. If omitted, first_build is the only build tested.')
parser.add_argument('-p', '--processes', help='Number of tests to run in parallel.', default=1, type=int)
parser.add_argument('--hook', help='Name of a python file to import for each test. The test will call before() and after() in this file. Used for our linux cronjob to start vncserver processes, for instance.')
parser.add_argument('--log', '-l', help="File to log progress to. Doesn't make sense for batched processes.")

##
##
##

logfile = None
def stat(msg=""):
  msg = "%s :: %s\n" % (time.ctime(), msg)
  sys.stdout.write("[run_slimtest.py] %s" % msg)
  if logfile:
    logfile.write(msg)
    logfile.flush()

def parse_nightly_time(string):
  string = string.split('-')
  if (len(string) != 3):
    raise Exception("Could not parse %s as a YYYY-MM-DD date")
  return datetime.date(int(string[0]), int(string[1]), int(string[2]))

def queue_builds(args):
  if not args['firstbuild']:
    raise Exception("--firstbuild is required")

  builds = []
  mode = args['mode']
  dorange = args['lastbuild']
  # Queue builds
  if mode == 'nightly':
    startdate = parse_nightly_time(args['firstbuild'])
    if dorange:
      enddate = parse_nightly_time(args['lastbuild'])
      dates = range(startdate.toordinal(), enddate.toordinal() + 1)
    else:
      dates = [ startdate.toordinal() ]
    for x in dates:
      builds.append(BuildGetter.NightlyBuild(datetime.date.fromordinal(x)))
  elif mode == 'tinderbox':
    startdate = float(args['firstbuild'])
    if dorange:
      enddate = float(args['lastbuild'])
      builds.extend(BuildGetter.get_tinderbox_builds(startdate, enddate))
    else:
      builds.append(BuildGetter.TinderboxBuild(startdate))
  else:
    raise Exception("Unknown mode %s" % mode)
  return builds

# Grab the first file (alphanumerically) from the batch folder,
# delete it and return its contents
def get_queued_job(dirname):
  batchfiles = os.listdir(dirname)
  if len(batchfiles):
    bname = os.path.join(dirname, sorted(batchfiles)[0])
    bfile = open(bname, 'r')
    bcmd = bfile.read()
    bfile.close()
    os.remove(bname)
    return bcmd
  return False

def test_build(build, buildnum, hook=None):
  mod = None
  try:
    if hook:
      mod = __import__(hook)
    if mod:
      mod.before(build, buildnum)
    ret = _test_build(build, buildnum)
  except (Exception, KeyboardInterrupt) as e:
    print("Test worker encountered an exception:\n%s :: %s" % (type(e), e))
    ret = False

  if mod:
    try:
      mod.after()
    except: pass
  return ret
  
def _test_build(build, buildindex):
  tester = BenchTester.BenchTester()

  # Load modules for tests we have
  for test in AreWeSlimYetTests.values():
    if not tester.load_module(test['type']):
      stat("Could not load module %s" % (test['type'],))
      return False
  
  # Setup tester
  testinfo = {
    'buildname': build.get_revision(),
    'binary': build.get_binary(),
    'buildtime': build.get_buildtime(),
    'sqlitedb': "slimtest.sqlite",
    'logfile': "slimtest.log",
    'jsbridge_port': 24243 + buildindex # Use different jsbridge ports so as not to collide
  }
  stat("Test %u starting :: %s" % (buildindex, testinfo))
  tester.setup(testinfo)
  
  # Run tests
  for testname, testinfo in AreWeSlimYetTests.items():
    if not tester.run_test(testname, testinfo['type'], testinfo['vars']):
      stat("SlimTest: Failed at test %s\n" % testname)
      return False
  
  return True

#
# Main
#

if __name__ == '__main__':
  args = vars(parser.parse_args())

  if args.get('log'):
    logfile = open(args.get('log'), 'a')

  pool = multiprocessing.Pool(processes=args['processes'])
  buildnum = 0
  running = []

  batchmode = args.get('batch')
  if batchmode:
    pending = []
  else:
    pending = queue_builds(args)

  while True:
    # Clean up finished builds
    def clean(task):
      if task.ready():
        if task.successful() and task.get():
          stat("Build %u <%s> finished" % (task.num, task.build.get_name()))
        else:
          stat("!! Build %u <%s> failed" % (task.num, task.build.get_name()))
        task.build.cleanup()
        return False
      return True
    running = filter(clean, running)
    
    while batchmode and len(running) + len(pending) < args['processes']:
      # Not enough work to fill workers, read in more jobs
      bcmd = get_queued_job(batchmode)
      if not bcmd: break
      pending.extend(queue_builds(vars(parser.parse_args(bcmd))))

    # Prepare pending builds and put them in the run pool, but not more than
    # max + 10, as prepared builds takeup space (hundreds of queued builds would
    # fill /tmp with gigabytes of things)
    if len(pending) and len(running) < args['processes'] + 10:
      build = pending[0]
      stat("Preparing build %u" % (buildnum,))
      build.prepare()
      run = pool.apply_async(test_build, [build, buildnum, args['hook']])
      run.build = build
      run.num = buildnum
      running.append(run)
      pending.remove(build)
      buildnum += 1
   
    if len(running) + len(pending) == 0:
      # out of things to do
      break
    else:
      # Wait a little and repeat loop
      stat("%u tasks :: %s" % (len(running), map(lambda x: x.num, running)))
      time.sleep(5)

  stat("No more tasks exiting")
  pool.close()
  pool.join()  

