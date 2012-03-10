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
import socket
import shlex
import platform
import sqlite3
import json

sys.path.append(os.path.abspath("benchtester"))
import BuildGetter

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

parser = argparse.ArgumentParser(description='Run the areweslimyet.com tests against one or more builds in parallel')
parser.add_argument('--mode', help='nightly or tinderbox or build')
parser.add_argument('--batch', help='Batch mode -- given a folder name, treat each file within as containing a set of arguments to this script, deleting each file as it is processed.')
parser.add_argument('--firstbuild', help='For nightly, the date (YYYY-MM-DD) of the first build to test. For tinderbox, the timestamp to start testing builds at. For build, the first revision to build.')
parser.add_argument('--lastbuild', help='[optional] For nightly builds, the last date to test. For tinderbox, the timestamp to stop testing builds at. For build, the last revision to build If omitted, first_build is the only build tested.')
parser.add_argument('-p', '--processes', help='Number of tests to run in parallel.', default=1, type=int)
parser.add_argument('--hook', help='Name of a python file to import for each test. The test will call before() and after() in this file. Used for our linux cronjob to start vncserver processes, for instance.')
parser.add_argument('--logdir', '-l', help="Directory to log progress to. Doesn't make sense for batched processes. Creates 'tester.log', 'buildname.test.log' and 'buildname.build.log' (for compile builds).")
parser.add_argument('--repo', help="For build mode, the checked out FF repo to use")
parser.add_argument('--mozconfig', help="For build mode, the mozconfig to use")
parser.add_argument('--objdir', help="For build mode, the objdir provided mozconfig will create")
parser.add_argument('--no-pull', action='store_true', help="For build mode, don't run a hg pull in the repo before messing with a commit")
parser.add_argument('--status-file', help="A file to keep a json-dump of the currently running job status in. This file is mv'd into place to avoid read/write issues")
parser.add_argument('--status-resume', action='store_true', help="Resume any jobs still present in the status file. Useful for interrupted sessions")
parser.add_argument('--skip-existing', action='store_true', help="Check the sqlite database and skip a build if it already has complete test data")
parser.add_argument('--prioritize', action='store_true', help="For batch'd builds, insert at the beginning of the pending queue rather than the end")

##
##
##

is_win = platform.system() == "Windows"
logfile = None
starttime = time.time()
sql = None

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

def have_test_data(build):
  global sql
  if not sql:
    if not os.path.exists('slimtest.sqlite'):
      return False
    sql = sqlite3.connect('slimtest.sqlite')
    sql.row_factory = sqlite3.Row

  res = sql.execute("SELECT `id` FROM `benchtester_builds` WHERE `name` = ?", [build.fullrev])
  row = res.fetchone()
  if not row: return False

  res = sql.execute("SELECT `name` FROM `benchtester_tests` WHERE `successful` = 1 AND `build_id` = ?", [row['id']])
  have_tests = set(map(lambda x: x['name'], res.fetchall()))
  for x in AreWeSlimYetTests:
    if not x in have_tests:
      return False
  stat("Skipping build with test data: %s" % (build.fullrev,))
  return True

# Builds that are in the pending/running list already
def build_is_queued(build):
  global pending, running
  for x in running + pending:
    if type(x) == type(build) and x.get_revision() == build.get_revision():
      return True
  return False
  
def check_builds(buildlist):
    def filter_unknown_builds(build):
      if build.get_revision() and get_full_revision(build):
        return True
      else:
        build.note = "Could not find revision information in repository"
        build.fullrev = "unknown"
        do_complete(build, True)
        return False

    def filter_existing_builds(build):
      if build_is_queued(build):
        build.note = "Build is duplicate of already-queued build -- skipped";
        do_complete(build, True)
        return False
      if have_test_data(build):
        build.note = "Build has complete test data -- skipped";
        do_complete(build, True)
        return False
      return True
    # Remove builds that have no revision (not found on ftp.m.o, usually)
    # or can't be fully looked up
    buildlist = filter(filter_unknown_builds, buildlist)
    if gArgs.get('skip_existing') or args.get('skip_existing'):
      buildlist = filter(filter_existing_builds, buildlist)
    return buildlist
    stat("Queued %u builds" % (len(buildlist),))

def queue_builds(args):
  if not args['firstbuild']:
    raise Exception("--firstbuild is required")

  if not gArgs.get('no_pull'):
    # Do a tip lookup to pull the repo so get_full_revision is up to date
    BuildGetter.get_hg_range(gArgs.get('repo'), '.', '.', True)

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
      builds.extend(check_builds([BuildGetter.NightlyBuild(datetime.date.fromordinal(x))]))
  elif mode == 'tinderbox':
    startdate = float(args['firstbuild'])
    if dorange:
      enddate = float(args['lastbuild'])
      builds.extend(check_builds(BuildGetter.get_tinderbox_builds(startdate, enddate)))
    else:
      builds.extend(check_builds([BuildGetter.TinderboxBuild(startdate)]))
  elif mode == 'build':
    repo = args.get('repo') if args.get('repo') else gArgs.get('repo')
    objdir = args.get('objdir') if args.get('objdir') else gArgs.get('objdir')
    mozconfig = args.get('mozconfig') if args.get('mozconfig') else gArgs.get('mozconfig')
    if not repo or not mozconfig or not objdir:
      raise Exception("Build mode requires --repo, --mozconfig, and --objdir to be set")

    if dorange:
      lastbuild = args['lastbuild']
    else:
      lastbuild = args['firstbuild']
    for commit in BuildGetter.get_hg_range(repo, args['firstbuild'], lastbuild, not args.get("no_pull")):
      if gArgs.get('logdir'):
        logfile = os.path.join(gArgs.get('logdir'), "%s.build.log" % (commit,))
      else:
        logfile = None
      builds.extend(check_builds([BuildGetter.CompileBuild(repo, mozconfig, objdir, pull=True, commit=commit, log=logfile)]))
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

# For writing builds to the status.json file, as well as resuming an interrupted
# session by parsing that file.
def serialize_build(build):
  ret = {
    'timestamp' : build.get_buildtime(),
    'revision' : build.fullrev
  }
  if hasattr(build, 'note'):
    ret['note'] = build.note
  if hasattr(build, 'started'):
    ret['started'] = build.started
  if hasattr(build, 'completed'):
    ret['completed'] = build.completed

  if isinstance(build, BuildGetter.CompileBuild):
    ret['type'] = 'compile'
  elif isinstance(build, BuildGetter.TinderboxBuild):
    ret['type'] = 'tinderbox'
  elif isinstance(build, BuildGetter.NightlyBuild):
    # Date of nightly might not correspond to build timestamp
    ret['for'] = '%u-%u-%u' % (build._date.year, build._date.month, build._date.day)
    ret['type'] = 'nightly'
  else:
    raise Exception("Unknown build type %s" % (build,))
  return ret

def deserialize_builds(inbuilds):
  builds = []
  for buildobj in inbuilds:
    if buildobj['type'] == 'compile':
      builds.append(BuildGetter.CompileBuild(gArgs.get('repo'), gArgs.get('mozconfig'), gArgs.get('objdir'), pull=True, commit=buildobj['revision'], log=None))
    elif buildobj['type'] == 'tinderbox':
      builds.append(BuildGetter.TinderboxBuild(buildobj['timestamp']))
    elif buildobj['type'] == 'nightly':
      builds.append(BuildGetter.NightlyBuild(parse_nightly_time(buildobj['for'])))
    else:
      raise Exception("Unkown build type %s" % buildobj['type'])
  return check_builds(builds)

def test_build(build, buildnum, fullrev, hook=None):
  mod = None
  try:
    if hook:
      mod = __import__(hook)
    if mod:
      mod.before(build, buildnum)
    ret = _test_build(build, buildnum, fullrev)
  except (Exception, KeyboardInterrupt) as e:
    err = "Test worker encountered an exception:\n%s :: %s" % (type(e), e)
    stat(err)
    ret = err

  if mod:
    try:
      mod.after()
    except: pass
  return ret
  
def _test_build(build, buildindex, fullrev):
  import BenchTester
  tester = BenchTester.BenchTester()

  # Load modules for tests we have
  for test in AreWeSlimYetTests.values():
    if not tester.load_module(test['type']):
      err = "Could not load module %s" % (test['type'],)
      stat(err)
      return err
  
  # Setup tester
  # TODO BenchTester should actually dynamically pick a free port, rather than
  # taking it as a parameter.
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  try:
    s.bind(('', 24242 + buildindex))
  except Exception, e:
    stat("WARNING: Port %u unavailable" % (24242 + buildindex,))
  s.close()

  if gArgs.get('logdir'):
    logfile = os.path.join(gArgs.get('logdir'), "%s.test.log" % (fullrev,))
  else:
    logfile = None
  testinfo = {
    'buildname': fullrev,
    'binary': build.get_binary(),
    'buildtime': build.get_buildtime(),
    'sqlitedb': "slimtest.sqlite",
    'logfile': logfile,
    'jsbridge_port': 24242 + buildindex # Use different jsbridge ports so as not to collide
  }
  stat("Test %u starting :: %s" % (buildindex, testinfo))
  tester.setup(testinfo)
  
  # Run tests
  for testname, testinfo in AreWeSlimYetTests.items():
    if not tester.run_test(testname, testinfo['type'], testinfo['vars']):
      err = "SlimTest: Failed at test %s\n" % testname
      stat(err)
      return err
  
  return True

def do_complete(build, fail=False):
  global failed, completed
  build.completed = time.time()
  if fail:
    failed.append(build)
  else:
    completed.append(build)
  
def get_full_revision(build):
  build.fullrev = build.get_revision()
  if len(build.fullrev) < 40:
    # We want the full revision ID for database
    revinfo = BuildGetter.get_hg_range(gArgs.get("repo"), build.fullrev, build.fullrev)
    if revinfo and len(revinfo):
      build.fullrev = revinfo[0]
    else:
      stat("!! Failed to lookup full commit ID for build %u" % (buildnum,))
      build.fullrev = None
      return False
  return True

def write_status(outfile, preparing=None):
  global pending, completed, failed, running, batches
  status = {
            'starttime' : starttime,
            'pending' : map(serialize_build, pending),
            'completed' : map(serialize_build, completed),
            'failed' : map(serialize_build, failed),
            'running' : map(lambda x: serialize_build(x.build), running[:gArgs.get('processes')]),
            'queued' : map(lambda x: serialize_build(x.build), running[gArgs.get('processes'):]),
            'preparing': [],
            'batches' : batches
          }
  if preparing:
    status['preparing'].append(serialize_build(preparing))
  tempfile = os.path.join(os.path.dirname(statfile), ".%s" % os.path.basename(statfile))
  sf = open(tempfile, 'w')
  json.dump(status, sf, indent=2)
  if is_win:
    os.remove(statfile) # Can't do atomic renames on windows
  os.rename(tempfile, statfile)
  sf.close()

#
# Main
#

if __name__ == '__main__':
  def make_pool():
    return multiprocessing.Pool(processes=args['processes'], maxtasksperchild=1)

  # gArgs is the 'global args', which is different in batch processes than
  # the per-job args
  gArgs = args = vars(parser.parse_args())

  if not gArgs.get('repo'):
    raise Exception('--repo is required for resolving full commit IDs (even on non-compile builds)')

  statfile = args.get("status_file")
  
  if args.get('logdir'):
    logfile = open(os.path.join(args.get('logdir'), 'tester.log'), 'a')

  stat("Starting at %s with args \"%s\"" % (time.ctime(), sys.argv))

  pool = make_pool()

  buildnum = 0
  # Note: These are accessed as globals in some places
  running = []
  pending = []
  completed = []
  failed = []
  batches = []

  batchmode = args.get('batch')
  if batchmode:
    if statfile and os.path.exists(statfile) and args.get('status_resume'):
      sf = open(statfile, 'r')
      ostat = json.load(sf)
      sf.close()
      pending.extend(deserialize_builds(ostat['running'] + ostat['queued'] + ostat['preparing'] +  ostat['pending']))
  else:
    pending = queue_builds(args)

  while True:
    # Clean up finished builds
    def clean(task):
      if task.ready():
        taskresult = task.get() if task.successful() else False
        if taskresult is True:
          stat("Build %u finished" % (task.num,))
          do_complete(task.build)
        else:
          stat("!! Build %u failed" % (task.num,))
          task.build.note = "Task returned error %s" % (taskresult,)
          do_complete(task.build, True)
        task.build.cleanup()
        return False
      return True
    running = filter(clean, running)

    # Read any pending jobs if we're in batchmode
    while batchmode:
      bcmd = None
      rcmd = get_queued_job(batchmode)
      if not rcmd: break
      try:
        bcmd = vars(parser.parse_args(shlex.split(rcmd)))
      except SystemExit, e: # Don't let argparser actually exit on fail
        stat("Failed to parse batch file command: \"%s\"" % (rcmd,))
        ret = "Failed to parse arguments"
      if bcmd:
        try:
          newbuilds = queue_builds(bcmd)
          if bcmd['prioritize']:
            pending = newbuilds + pending
          else:
            pending.extend(newbuilds)
          ret = "Queued %u builds" % (len(newbuilds),)
        except Exception, e:
          ret = "Queuing builds triggered exception %s: %s" % (type(e), e)
      batches.append({ 'command': rcmd, 'result' : ret, 'processed' : time.time() })


    # Prepare pending builds and put them in the run pool, but not more than
    # max + 10, as prepared builds takeup space (hundreds of queued builds would
    # fill /tmp with gigabytes of things)
    if len(pending) and len(running) < args['processes'] * 2:
      build = pending[0]
      pending.remove(build)
      if statfile:
        write_status(statfile, build)
      stat("Preparing build %u :: %s" % (buildnum, serialize_build(build)))
      if build.prepare():
        run = pool.apply_async(test_build, [build, buildnum, build.fullrev, args['hook']])
        run.build = build
        run.num = buildnum
        run.build.started = time.time()
        running.append(run)
      else:
        stat("!! Failed to prepare build %u" % (buildnum,))
      buildnum += 1

    if statfile:
        write_status(statfile)
    if len(running) + len(pending) == 0:
      # out of things to do
      if batchmode:
        if buildnum > 0:
          stat("All tasks complete. Resetting")
          # Reset buildnum when empty to keep it from getting too large
          # (it affects vnc display # and such, which isn't infinite)
          buildnum = 0
          # Remove items older than 1 day from these lists
          completed = filter(lambda x: (x.completed + 60 * 60 * 24) > time.time(), completed)
          failed = filter(lambda x: (x.completed + 60 * 60 * 24) > time.time(), failed)
          batches = filter(lambda x: (x.processed + 60 * 60 * 24) > time.time(), batches)
        else:
          time.sleep(10)
      else:
        break
    else:
      # Wait a little and repeat loop
      time.sleep(5)

  stat("No more tasks exiting")
  if statfile:
    write_status(statfile)
  pool.close()
  pool.join()
