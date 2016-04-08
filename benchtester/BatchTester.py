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
import platform
import sqlite3
import json
import pickle

import BuildGetter

##
##
##

is_win = platform.system() == "Windows"

##
# Utility
##


def parse_nightly_time(string):
    string = string.split('-')
    if (len(string) != 3):
        raise Exception("Could not parse %s as a YYYY-MM-DD date")
    return datetime.date(int(string[0]), int(string[1]), int(string[2]))

# Grab the first file (alphanumerically) from the batch folder,
# delete it and return its contents


def get_queued_job(dirname):
    batchfiles = os.listdir(dirname)
    if len(batchfiles):
        bname = os.path.join(dirname, sorted(batchfiles)[0])
        try:
            bfile = open(bname, 'r')
            bcmd = json.load(bfile)
        finally:
            if bfile:
                bfile.close()
            os.remove(bname)
        return bcmd
    return False

# Given a 'hook', which is a path to a python file,
# imports it as a module and returns the handle. A bit hacky.


def _get_hook(filename):
    hookname = os.path.basename(filename)
    # Strip .py and complain if it has other periods. (I said hacky!)
    if hookname[-3:].lower() == '.py':
        hookname = hookname[:-3]
    if hookname.find('.') != -1:
        raise Exception(
            "Hook filename cannot contain periods (other than .py (it is "
            "imported as a module interally))")

    # Add dir containing hook to path temporarily
    sys.path.append(os.path.abspath(os.path.dirname(filename)))
    try:
        ret = __import__(hookname)
    finally:
        sys.path = sys.path[:-1]
    return ret

# BatchBuild wraps BuildGetter.build with various info, and provides
# a .(de)serialize for the status.json file output


class BatchBuild():

    def __init__(self, build, revision):
        # BuildGetter compilebuild object
        self.build = build
        # Revision, may be full hash or partial
        self.revision = revision
        # Build / task number. These are sequential, but reset to zero occasionally
        # no two *concurrently running* builds will share a number, so it can be
        # used for e.g. non-colliding VNC display #s
        self.num = None
        # The pool task associated with this build
        self.task = None
        # Textual note for this build, shows up in logs and serialized Build objects.
        # used by AWSY's /status/ page, for instance
        self.note = None
        # Place in a custom series
        self.series = None
        # Timestamp of when the build began testing
        self.started = None
        # unique identifier per session, totally unique unlike .num. TODO should
        # probably be given to __init__ instead of set manually later...
        self.uid = -1
        # Timestamp of when this build was 'finished' (failed or otherwise)
        self.finished = None
        # If true, retest the build even if its already queued. --hook scripts should
        # honor this in should_test as well
        self.force = None

    def build_type(self):
        if isinstance(self.build, BuildGetter.CompileBuild):
            return 'compile'
        elif isinstance(self.build, BuildGetter.TryBuild):
            return 'try'
        elif isinstance(self.build, BuildGetter.FTPBuild):
            return 'ftp'
        elif isinstance(self.build, BuildGetter.TinderboxBuild):
            return 'tinderbox'
        elif isinstance(self.build, BuildGetter.NightlyBuild):
            return 'nightly'
        else:
            raise Exception("Unknown build type %s" % (self.build,))

    @staticmethod
    def deserialize(buildobj, args):
        if buildobj['type'] == 'compile':
            # See https://github.com/mozilla/areweslimyet/issues/47
            raise Exception("Build type 'compile' is not currently supported")
        elif buildobj['type'] == 'tinderbox':
            build = BuildGetter.TinderboxBuild(
                buildobj['timestamp'], buildobj['branch'])
        elif buildobj['type'] == 'nightly':
            build = BuildGetter.NightlyBuild(
                parse_nightly_time(buildobj['for']))
        elif buildobj['type'] == 'ftp':
            build = BuildGetter.FTPBuild(buildobj['path'])
        elif buildobj['type'] == 'try':
            build = BuildGetter.TryBuild(buildobj['changeset'])
        else:
            raise Exception("Unkown build type %s" % buildobj['type'])

        ret = BatchBuild(build, buildobj['revision'])
        ret.series = buildobj['series']
        ret.uid = buildobj['uid']
        ret.timestamp = buildobj['timestamp']
        ret.note = buildobj['note']
        ret.started = buildobj['started']
        ret.finished = buildobj['finished']
        ret.force = buildobj['force']

        return ret

    def serialize(self):
        ret = {
            'timestamp': self.build.get_buildtime(),
            'revision': self.revision,
            'note': self.note,
            'started': self.started,
            'finished': self.finished,
            'force': self.force,
            'uid': self.uid,
            'series': self.series
        }

        build_type = self.build_type()
        ret['type'] = build_type

        if build_type == 'try':
            ret['changeset'] = self.build._changeset
        elif build_type == 'ftp':
            ret['path'] = self.build._path
        elif build_type == 'tinderbox':
            # When deserializing we need to look this up by it's tinderbox timestamp,
            # even if we use the push timestamp internally
            ret['timestamp'] = self.build.get_tinderbox_timestamp()
            ret['branch'] = self.build.get_branch()
        elif build_type == 'nightly':
            # Date of nightly might not correspond to build timestamp
            ret['for'] = '%u-%u-%u' % (self.build._date.year,
                                       self.build._date.month, self.build._date.day)

        return ret

# Work around multiprocessing.Pool() quirkiness. We can't give it
# BatchTest.test_build directly because that might not point to the same thing
# in the child process (members are mutable). we also can't give it build
# directly because the pool pickles it at a later date and causes thread issues
# (but just forcing it to pickle explicitly is fine as it would be pickled
# eventually either way)


def _pool_batchtest_build(build, args):
    return BatchTest.test_build(pickle.loads(build), args)

##
# BatchTest - a threaded test object. Given a list of builds, prepares them
# and tests them in parallel. In 'batch' mode, processes sets of
# arguments from a batch folder, and adds them to its queue, never
# exiting. (daemon mode might be better?)
# See BatchTestCLI for documentation on options
##


class BatchTest(object):

    def __init__(self, args, out=sys.stdout):
        # See BatchTestCLI for args documentation, for the time being
        self.args = args
        self.logfile = None
        self.out = out
        self.starttime = time.time()
        self.buildindex = 0
        self.pool = None
        self.processed = 0
        self.tick = 0
        self.builds = {
            'building': None,
            'prepared': [],
            'running': [],
            'pending': [],
            'skipped': [],
            'completed': [],
            'failed': []
        }
        self.processedbatches = []
        self.pendingbatches = []

        if (self.args.get('hook')):
            sys.path.append(os.path.abspath(
                os.path.dirname(self.args.get('hook'))))
            self.hook = os.path.basename(self.args.get('hook'))
        else:
            self.hook = None

        self.builder = None
        self.builder_mode = None
        self.builder_batch = None
        self.manager = multiprocessing.Manager()
        self.builder_result = self.manager.dict(
            {'result': 'not started', 'ret': None})

    def stat(self, msg=""):
        msg = "%s :: %s\n" % (time.ctime(), msg)
        if self.out:
            self.out.write("[BatchTester] %s" % msg)
        if self.logfile:
            self.logfile.write(msg)
            self.logfile.flush()

    #
    # Resets worker pool
    def reset_pool(self):
        if self.pool:
            self.pool.close()
            self.pool.join()
        self.buildindex = 0
        self.pool = multiprocessing.Pool(
            processes=self.args['processes'], maxtasksperchild=1)

    #
    # Writes/updates the status file
    def write_status(self):
        statfile = self.args.get('status_file')
        if not statfile:
            return
        status = {
            'starttime': self.starttime,
            'building': self.builds['building'].serialize() if self.builds['building'] else None,
            'batches': self.processedbatches,
            'pendingbatches': self.pendingbatches
        }
        for x in self.builds:
            if type(self.builds[x]) == list:
                status[x] = map(lambda y: y.serialize(), self.builds[x])

        tempfile = os.path.join(os.path.dirname(
            statfile), ".%s" % os.path.basename(statfile))
        sf = open(tempfile, 'w')
        json.dump(status, sf, indent=2)
        if is_win:
            os.remove(statfile)  # Can't do atomic renames on windows
        os.rename(tempfile, statfile)
        sf.close()

    # Builds that are in the pending/running list already
    def build_is_queued(self, build):
        for x in (self.builds['running'], self.builds['pending'],
                  self.builds['prepared'], [self.builds['building']]):
            for y in x:
                if y and y.revision == build.revision:
                    return True
        return False
    # Given a set of arguments, lookup & add all specified builds to our queue.
    # This happens asyncrhonously, so not all builds may be queued immediately

    def add_batch(self, batchargs):
        self.pendingbatches.append(
            {'args': batchargs, 'note': None, 'requested': time.time(), 'uid': self.processed})
        self.processed += 1

    # Checks on the builder subprocess, getting its result, starting it if needed,
    # etc
    def check_builder(self):
        # Did it exit?
        if self.builder and not self.builder.is_alive():
            self.builder.join()
            self.builder = None

            # Finished a batch queue job
            if self.builder_mode == 'batch':
                if self.builder_result['result'] == 'success':
                    queued = self.queue_builds(
                        self.builder_result['ret'][0],
                        prepend=self.builder_batch['args'].get('prioritize'))
                    already_queued = len(self.builder_result['ret'][0]) - len(queued)
                    self.queue_builds(
                        self.builder_result['ret'][1],
                        target='skipped',
                        prepend=self.builder_batch['args'].get('prioritize'))
                    self.builder_batch['note'] = "Queued %u builds, skipped %u" % (
                        len(queued), already_queued + len(self.builder_result['ret'][1]))
                else:
                    self.builder_batch['note'] = self.builder_result['ret']
                self.stat("Batch completed: %s (%s)" % (
                    self.builder_batch['args'], self.builder_batch['note']))
                self.builder_batch = None

            # Finished a build job
            elif self.builder_mode == 'build':
                build = self.builds['building']
                self.stat("Test %u prepared" % (build.num,))
                self.builds['building'] = None
                if self.builder_result['result'] == 'success':
                    self.builds['prepared'].append(self.builder_result['ret'])
                else:
                    build.note = "Build setup failed - see log"
                    build.finished = time.time()
                    self.builds['failed'].append(build)
            self.builder_result['result'] = 'uninitialied'
            self.builder_result['ret'] = None
            self.builder_mode = None

        # Should it run?
        if not self.builder and len(self.pendingbatches):
            self.builder_mode = 'batch'
            self.builder_batch = self.pendingbatches.pop()
            self.stat("Handling batch %s" % (self.builder_batch,))
            self.builder_batch['processed'] = time.time()
            self.processedbatches.append(self.builder_batch)
            self.builder_batch['note'] = "Processing - Looking up builds"
            self.builder = multiprocessing.Process(target=self._process_batch, args=(
                self.args, self.builder_batch['args'], self.builder_result, self.hook))
            self.builder.start()
        elif not self.builder and self.builds['building']:
            self.builder_mode = 'build'
            self.stat("Starting build for %s :: %s" % (
                self.builds['building'].num, self.builds['building'].serialize()))
            self.builder = multiprocessing.Process(target=self.prepare_build, args=(
                self.builds['building'], self.builder_result))
            self.builder.start()

    @staticmethod
    def prepare_build(build, result):
        if build.build.prepare():
            result['result'] = 'success'
        else:
            result['result'] = 'failed'

        result['ret'] = build

    # Add builds to self.builds[target], giving them a uid. Redirect builds from
    # pending -> skipped if they're already queued
    def queue_builds(self, builds, target='pending', prepend=False):
        skip = []
        ready = []
        for x in builds:
            if not x.force and target == 'pending' and self.build_is_queued(x):
                x.finished = time.time()
                skip.append(x)
                x.note = "A build with this revision is already in queue"
            else:
                ready.append(x)
            x.uid = self.processed
            self.processed += 1
        if len(skip):
            self.builds['skipped'].extend(skip)
        if (prepend):
            self.builds[target] = ready + self.builds[target]
        else:
            self.builds[target].extend(ready)
        return ready

    #
    # Run loop
    #
    def run(self):
        if not self.args.get('repo'):
            raise Exception(
                '--repo is required for resolving full commit IDs (even on non-compile builds)')

        statfile = self.args.get("status_file")

        if self.args.get('logdir'):
            self.logfile = open(os.path.join(
                self.args.get('logdir'), 'tester.log'), 'a')

        self.stat("Starting at %s with args \"%s\"" % (time.ctime(), sys.argv))

        self.reset_pool()

        batchmode = self.args.get('batch')
        if batchmode:
            if statfile and os.path.exists(statfile) and self.args.get('status_resume'):
                sf = open(statfile, 'r')
                ostat = json.load(sf)
                sf.close()
                # Try to recover builds in order they were going to be
                # processed
                recover_builds = ostat['running']
                recover_builds.extend(ostat['prepared'])
                if ostat['building']:
                    recover_builds.append(ostat['building'])
                recover_builds.extend(ostat['pending'])

                if len(recover_builds):
                    # Create a dummy batch, process it on main thread, move it to completed.
                    # this all happens before the helper thread starts so there are no other
                    # batches to contend with
                    self.add_batch(
                        "< Tester Restarted : Resuming any interrupted builds >")
                    resumebatch = self.pendingbatches.pop()
                    self.processedbatches.append(resumebatch)
                    resumebatch['processed'] = time.time()
                    self.write_status()
                    self.queue_builds(
                        map(lambda x: BatchBuild.deserialize(x, self.args), recover_builds))
                    resumebatch['note'] = "Recovered %u builds (%u skipped)" % (
                        len(self.builds['pending']), len(self.builds['skipped']))
        else:
            self.add_batch(self.args)

        while True:
            # Clean up finished builds
            for build in self.builds['running']:
                if not build.task.ready():
                    continue

                taskresult = build.task.get() if build.task.successful() else False
                if taskresult is True:
                    self.stat("Test %u finished" % (build.num,))
                    self.builds['completed'].append(build)
                else:
                    self.stat("!! Test %u failed :: %s" %
                              (build.num, taskresult))
                    build.note = "Failed: %s" % (taskresult,)
                    self.builds['failed'].append(build)
                build.finished = time.time()
                self.builds['running'].remove(build)
                build.build.cleanup()

            # Check on builder
            self.check_builder()

            # Read any pending jobs if we're in batchmode
            while batchmode:
                rcmd = None
                try:
                    rcmd = get_queued_job(batchmode)
                except Exception, e:
                    note = "Invalid batch file"
                    self.stat(note)
                    self.processedbatches.append(
                        {'args': "<parse error>", 'note': note})
                if rcmd:
                    self.add_batch(rcmd)
                else:
                    break

            # Prepare pending builds, but not more than processes, as prepared builds
            # takeup space (hundreds of queued builds would fill /tmp with gigabytes
            # of things)
            if len(self.builds['pending']) \
                    and not self.builds['building'] \
                    and len(self.builds['prepared']) < self.args['processes']:
                build = self.builds['pending'][0]
                self.builds['building'] = build
                self.builds['pending'].remove(build)
                build.num = self.buildindex
                self.buildindex += 1

            # Start builds if pool is not filled
            while len(self.builds['prepared']) \
                    and len(self.builds['running']) < self.args['processes']:
                build = self.builds['prepared'][0]
                self.builds['prepared'].remove(build)
                build.started = time.time()
                self.stat("Moving test %u to running" % (build.num,))
                build.task = self.pool.apply_async(
                    _pool_batchtest_build, [pickle.dumps(build), self.args])
                self.builds['running'].append(build)

            self.write_status()

            in_progress = sum(
                len(self.builds['pending']),
                len(self.builds['prepared']),
                len(self.builds['running']))

            if not self.builder and not self.builds['building'] and in_progress == 0:
                # Out of things to do
                if batchmode and self.buildindex > 0:
                    # In batchmode, reset the pool and restore buildindex to zero.
                    # Buildindex is used for things like VNC display IDs, so we don't want
                    # it to get too high.
                    self.reset_pool()
                    self.buildindex = 0
                elif not batchmode:
                    self.stat("All tasks complete, exiting")
                    break  # Done
            # Wait a little and repeat loop
            time.sleep(1)
            self.tick += 1
            if self.tick % 120 == 0:
                # Remove items older than 1 day from these lists
                self.builds['completed'] = filter(lambda x: (
                    x.finished + 60 * 60 * 24) > time.time(), self.builds['completed'])
                self.builds['failed'] = filter(lambda x: (
                    x.finished + 60 * 60 * 24 * 3) > time.time(), self.builds['failed'])
                self.builds['skipped'] = filter(lambda x: (
                    x.finished + 60 * 60 * 24) > time.time(), self.builds['skipped'])
                self.processedbatches = filter(lambda x: (
                    x['processed'] + 60 * 60 * 24) > time.time(), self.processedbatches)
            time.sleep(1)

        self.stat("No more tasks, exiting")
        self.pool.close()
        self.pool.join()
        self.pool = None

    # Threaded call the builder is started on. Calls _process_batch_inner and
    # handles return results
    @staticmethod
    def _process_batch(globalargs, batchargs, returnproxy, hook):
        try:
            if hook:
                mod = _get_hook(globalargs.get('hook'))
            else:
                mod = None
            ret = BatchTest._process_batch_inner(globalargs, batchargs, mod)
        except Exception, e:
            import traceback
            traceback.print_exc()
            ret = "An exception occured while processing batch -- %s: %s" % (
                type(e), e)

        if type(ret) == str:
            returnproxy['result'] = 'error'
        else:
            returnproxy['result'] = 'success'
        returnproxy['ret'] = ret

    #
    # Inner call for _process_batch
    @staticmethod
    def _process_batch_inner(globalargs, batchargs, hook):
        if not batchargs['firstbuild']:
            raise Exception("--firstbuild is required")

        mode = batchargs['mode']
        dorange = 'lastbuild' in batchargs and batchargs['lastbuild']
        builds = []
        # Queue builds
        if mode == 'nightly':
            startdate = parse_nightly_time(batchargs['firstbuild'])
            if dorange:
                enddate = parse_nightly_time(batchargs['lastbuild'])
                dates = range(startdate.toordinal(), enddate.toordinal() + 1)
            else:
                dates = [startdate.toordinal()]
            for x in dates:
                builds.append(BuildGetter.NightlyBuild(
                    datetime.date.fromordinal(x)))
        elif mode == 'tinderbox':
            startdate = float(batchargs['firstbuild'])
            if dorange:
                enddate = float(batchargs['lastbuild'])
                tinderbuilds = BuildGetter.list_tinderbox_builds(
                    startdate, enddate)
                for x in tinderbuilds:
                    builds.append(BuildGetter.TinderboxBuild(x))
            else:
                builds.append(BuildGetter.TinderboxBuild(startdate))
        elif mode == 'ftp':
            path = batchargs['firstbuild']
            builds.append(BuildGetter.FTPBuild(path))
        elif mode == 'try':
            path = batchargs['firstbuild']
            builds.append(BuildGetter.TryBuild(path))
        elif mode == 'compile':
            # See https://github.com/mozilla/areweslimyet/issues/47
            raise Exception("Build type 'compile' is not currently supported")
        else:
            raise Exception("Unknown mode %s" % mode)

        readybuilds = []
        skippedbuilds = []
        force = batchargs.get('force') if batchargs.get(
            'force') else globalargs.get('force')
        for build in builds:
            rev = build.get_revision()
            # HACKITY HACK HACK HACK
            build._scraper = None

            build = BatchBuild(build, rev)
            build.force = force
            build.series = batchargs.get('series')
            if not build.build.get_valid():
                # Can happen with FTP builds we failed to lookup on ftp.m.o, or any
                # builds that arn't found in pushlog
                build.note = "Build is not found or missing from pushlog"
            elif hook and not hook.should_test(build, globalargs):
                if not build.note:
                    build.note = "Build skipped by tester"
            else:
                readybuilds.append(build)
                continue

            build.finished = time.time()
            skippedbuilds.append(build)

        return [readybuilds, skippedbuilds]

    #
    # Build testing pool
    #
    @staticmethod
    def test_build(build, globalargs):
        mod = None
        ret = True
        if not globalargs.get('hook'):
            return "Cannot test builds without a --hook providing run_tests(Build)"

        try:
            mod = _get_hook(globalargs.get('hook'))
            # TODO BenchTester should actually dynamically pick a free port, rather than
            # taking it as a parameter.
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.bind(('', 24242 + build.num))
            except Exception, e:
                raise Exception(
                    "Test error: jsbridge port %u unavailable" % (24242 + build.num,))
            s.close()

            mod.run_tests(build, globalargs)
        except (Exception, KeyboardInterrupt) as e:
            err = "%s :: %s" % (type(e), e)
            ret = err
        return ret


class BatchTestCLI(BatchTest):

    def __init__(self, args=sys.argv[1:]):
        self.parser = argparse.ArgumentParser(
            description='Run tests against one or more builds in parallel')
        self.parser.add_argument('--mode',
                                 help='nightly or tinderbox or compile')
        self.parser.add_argument('--batch',
                                 help='Batch mode -- given a folder name, treat each file within '
                                      'as containing a set of arguments to this script, deleting '
                                      'each file as it is processed.')
        self.parser.add_argument('--firstbuild',
                                 help='For nightly, the date (YYYY-MM-DD) of the first build to '
                                      'test. For tinderbox, the timestamp to start testing builds '
                                      'at. For build, the first revision to build.')
        self.parser.add_argument('--lastbuild',
                                 help='[optional] For nightly builds, the last date to test. For '
                                      'tinderbox, the timestamp to stop testing builds at. For '
                                      'build, the last revision to build If omitted, first_build '
                                      'is the only build tested.')
        self.parser.add_argument('-p', '--processes',
                                 help='Number of tests to run in parallel.',
                                 default=multiprocessing.cpu_count(), type=int)
        self.parser.add_argument('--hook',
                                 help='Name of a python file to import for each test. The test '
                                      'will call should_test(BatchBuild), run_tests(BatchBuild), '
                                      'and cli_hook(argparser) in this file.')
        self.parser.add_argument('--logdir', '-l',
                                 help="Directory to log progress to. Doesn't make sense for "
                                      "batched processes. Creates 'tester.log', "
                                      "'buildname.test.log' and 'buildname.build.log' (for "
                                      "compile builds).")
        self.parser.add_argument('--repo',
                                 help="For build mode, the checked out FF repo to use")
        self.parser.add_argument('--mozconfig',
                                 help="For build mode, the mozconfig to use")
        self.parser.add_argument('--objdir',
                                 help="For build mode, the objdir provided mozconfig will create")
        self.parser.add_argument('--no-pull', action='store_true',
                                 help="For build mode, don't run a hg pull in the repo before "
                                      "messing with a commit")
        self.parser.add_argument('--status-file',
                                 help="A file to keep a json-dump of the currently running job "
                                      "status in. This file is mv'd into place to avoid "
                                      "read/write issues")
        self.parser.add_argument('--status-resume', action='store_true',
                                 help="Resume any jobs still present in the status file. Useful "
                                      "for interrupted sessions")
        self.parser.add_argument('--prioritize', action='store_true',
                                 help="For batch'd builds, insert at the beginning of the pending "
                                      "queue rather than the end")
        self.parser.add_argument('--force', action='store_true',
                                 help="Test/queue given builds even if they have already been "
                                      "tested or are already in queue")
        temp = vars(self.parser.parse_known_args(args)[0])
        if temp.get('hook'):
            mod = _get_hook(temp.get('hook'))
            mod.cli_hook(self.parser)

        args = vars(self.parser.parse_args(args))
        super(BatchTestCLI, self).__init__(args)

#
# Main
#

if __name__ == '__main__':
    cli = BatchTestCLI()
    cli.run()
