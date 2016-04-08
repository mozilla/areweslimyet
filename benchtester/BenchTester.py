#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2012 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import mercurial
import mercurial.ui
import mercurial.hg
import mercurial.commands
import os
import re
import sqlite3
import sys
import time

from mozlog.structured import commandline

# Database version, bump this when incompatible DB changes are made
gVersion = 1

gTableSchemas = [
    # benchtester_version - the database version, can be used for upgrade
    # scripts
    '''CREATE TABLE IF NOT EXISTS
      "benchtester_version" ("version" INTEGER NOT NULL UNIQUE)''',

    # Builds - info on builds we have tests for
    '''CREATE TABLE IF NOT EXISTS
      "benchtester_builds" ("id" INTEGER PRIMARY KEY NOT NULL,
                           "name" VARCHAR NOT NULL UNIQUE,
                           "time" DATETIME NOT NULL,
                           "repo_id" INTEGER NOT NULL)''',

    # Tests - tests that have been run and against which build
    '''CREATE TABLE IF NOT EXISTS
      "benchtester_tests" ("id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                          "name" VARCHAR NOT NULL,
                          "time" DATETIME NOT NULL,
                          "build_id" INTEGER NOT NULL,
                          "successful" INTEGER NOT NULL)''',

    # Datapoints - names of datapoints
    '''CREATE TABLE IF NOT EXISTS
      "benchtester_datapoints" ("id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                                "name" VARCHAR NOT NULL UNIQUE)''',

    # Procs - names of processes
    '''CREATE TABLE IF NOT EXISTS
      "benchtester_procs" ("id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                           "name" VARCHAR NOT NULL UNIQUE)''',

    # Repos - names of source repositories
    '''CREATE TABLE IF NOT EXISTS
      "benchtester_repos" ("id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                           "name" VARCHAR NOT NULL UNIQUE)''',

    # Checkpoints - names of checkpoints
    '''CREATE TABLE IF NOT EXISTS
      "benchtester_checkpoints" ("id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                                 "name" VARCHAR NOT NULL UNIQUE)''',

    # Data - datapoints from tests
    '''CREATE TABLE IF NOT EXISTS
      "benchtester_data" ("test_id" INTEGER NOT NULL,
                          "datapoint_id" INTEGER NOT NULL,
                          "checkpoint_id" INTEGER NOT NULL,
                          "proc_id" INTEGER NOT NULL,
                          "iteration" INTEGER NOT NULL,
                          "value" INTEGER NOT NULL,
                          "units" INTEGER NOT NULL,
                          "kind" INTEGER NOT NULL)''',

    # Some default indexes
    '''CREATE INDEX IF NOT EXISTS
       test_lookup ON benchtester_tests ( name, build_id DESC )''',
    '''CREATE INDEX IF NOT EXISTS
       data_for_test ON benchtester_data ( test_id DESC, datapoint_id )'''
]

# TODO:
# - doxygen or at least some sort of documentation
# - Add indexes to sqlitedb by default
# - add more self.info checkpoints
#
# - Test and fix if necessary on OS X / Win

# Runs the marionette memory tests and generates/updates a json data object with
# results
# - Currently used to graph the data on areweslimyet.com. The areweslimyet repo
#   is a good example of using this, given the lack of docs


class BenchTest():

    def __init__(self, parent):
        self.tester = parent
        self.name = "Unconfigured Test Module"

    def run_test(self, testname, testvars={}):
        return self.error("run_test() not defined")

    def setup(self):
        return True

    def error(self, msg):
        return self.tester.error("[%s] %s" % (self.name, msg))

    def warn(self, msg):
        return self.tester.warn("[%s] %s" % (self.name, msg))

    def info(self, msg):
        return self.tester.info("[%s] %s" % (self.name, msg))

# The main class for running tests


class BenchTester():

    def info(self, msg):
        self.logger.info(msg)

    def error(self, msg):
        self.errors.append(msg)
        self.logger.error(msg)
        return False

    def warn(self, msg):
        self.warnings.append(msg)
        self.logger.warning(msg)

    def run_test(self, testname, testtype, testvars={}):
        if not self.ready:
            return self.error("run_test() called before setup")

        # make sure a record is created, even if no testdata is produced
        if not self._open_db():
            return self.error("Failed to open sqlite database")

        if testtype in self.modules:
            self.info("Passing test '%s' to module '%s'" %
                      (testname, testtype))
            return self.modules[testtype].run_test(testname, testvars)
        else:
            return self.error("Test '%s' is of unknown type '%s'" % (testname, testtype))

    # Modules are named 'SomeModule.py' and have a class named 'SomeModule'
    # based on BenchTest
    def load_module(self, modname):
        if self.ready:
            return self.error("Modules must be loaded before setup()")

        if modname in self.modules:
            return True

        self.info("Loading module '%s'" % (modname))
        try:
            module = __import__(modname)
            self.modules[modname] = vars(module)[modname](self)
        except Exception, e:
            return self.error("Failed to load module '%s', Exception '%s': %s" %
                              (modname, type(e), e))

        return True

    @staticmethod
    def map_process_names(process_names):
        # Normalize the process names.
        # Given: [ "Main", "Web Content (123)", "Web Content (345)", "Web Content (678)" ]
        # Mapping: [ "Main" => "Main",
        #            "Web Content (123)" => "Web Content",
        #            "Web Content (345)" => "Web Content 2",
        #            "Web Content (678)" => "Web Content 3"
        #          ]
        proc_name_counts = {}
        proc_name_mapping = {}

        for full_process_name in process_names:
            # Drop the pid portion of process name
            process_re = r'(.*)\s+\(.+\)'
            m = re.match(process_re, full_process_name)
            if m:
                proc_name = m.group(1)
                if proc_name in proc_name_counts:
                    proc_name_counts[proc_name] += 1
                    proc_name_mapping[full_process_name] = "%s %d" % (
                        proc_name, proc_name_counts[proc_name])
                else:
                    # Leave the first entry w/o a number
                    proc_name_counts[proc_name] = 1
                    proc_name_mapping[full_process_name] = proc_name
            else:
                proc_name_mapping[full_process_name] = full_process_name

        return proc_name_mapping

    def insert_results(self, test_id, results):
        # - results is an array of iterations
        # - iterations is an array of checkpoints
        # - checkpoint is a dict with: label, reports
        # - reports is a dict of processes
        cur = self.sqlite.cursor()

        for x, iteration in enumerate(results):
            iternum = x + 1
            for checkpoint in iteration:
                label = checkpoint['label']

                # insert checkpoint name, get checkpoint_id
                cur.execute(
                    "SELECT id FROM benchtester_checkpoints WHERE name = ?", (label, ))
                row = cur.fetchone()
                checkpoint_id = row[0] if row else None
                if checkpoint_id is None:
                    cur.execute(
                        "INSERT INTO benchtester_checkpoints(name) VALUES (?)", (label, ))
                    checkpoint_id = cur.lastrowid

                proc_name_mapping = self.map_process_names(
                    checkpoint['reports'])
                for process_name, reports in checkpoint['reports'].iteritems():
                    # reports is a dictionary of datapoint_name: { val, unit,
                    # kind }
                    process_name = proc_name_mapping[process_name]

                    # insert process name, get process_id
                    cur.execute(
                        "SELECT id FROM benchtester_procs WHERE name = ?", (process_name, ))
                    row = cur.fetchone()
                    process_id = row[0] if row else None
                    if process_id is None:
                        cur.execute(
                            "INSERT INTO benchtester_procs(name) VALUES (?)", (process_name, ))
                        process_id = cur.lastrowid

                    # insert datapoint names
                    insertbegin = time.time()
                    self.info("Inserting %u datapoints into DB" % len(reports))
                    cur.executemany("INSERT OR IGNORE INTO `benchtester_datapoints`(name) "
                                    "VALUES (?)",
                                    ([k] for k in reports.iterkeys()))
                    self.sqlite.commit()
                    self.info("Filled datapoint names in %.02fs" %
                              (time.time() - insertbegin))

                    # insert datapoint values
                    insertbegin = time.time()
                    cur.executemany("INSERT INTO `benchtester_data` "
                                    "SELECT ?, p.id, ?, ?, ?, ?, ?, ? "
                                    "FROM `benchtester_datapoints` p "
                                    "WHERE p.name = ?",
                                    ([test_id,
                                        checkpoint_id,
                                        process_id,
                                        iternum,
                                        dp['val'],
                                        dp['unit'],
                                        dp['kind'],
                                        name]
                                     for name, dp in reports.iteritems() if dp))
                    self.sqlite.commit()
                    self.info("Filled datapoint values in %.02fs" %
                              (time.time() - insertbegin))

    # datapoints a list of the format [ [ "key", value, "meta"], ... ].
    # Duplicate keys are allowed. Value is numeric and required, meta is an
    # optional string (see db format)
    def add_test_results(self, testname, datapoints, succeeded=True):
        # Ensure DB is open
        if not self._open_db():
            return self.error("Failed to open sqlite database")

        if not testname:
            return self.error("Invalid use of addDataPoint()")

        timestamp = time.time()

        if self.sqlite:
            try:
                cur = self.sqlite.cursor()
                cur.execute("INSERT INTO "
                            "  benchtester_tests(name, time, build_id, successful) "
                            "VALUES (?, ?, ?, ?)",
                            (testname, int(timestamp), self.build_id, succeeded))
                cur.execute("SELECT last_insert_rowid()")

                if datapoints:
                    testid = cur.fetchone()[0]
                    self.insert_results(testid, datapoints)
            except Exception, e:
                self.error(
                    "Failed to insert data into sqlite, got '%s': %s" % (type(e), e))
                import traceback
                traceback.print_exc()
                self.sqlite.rollback()
                return False
        return True

    def __init__(self, logfile=None, out=sys.stdout):
        self.starttime = time.clock()
        self.ready = False
        self.args = {}
        self.argparser = argparse.ArgumentParser(
            description='Run automated benchmark suite, optionally adding \
                         datapoints to a sqlite database')
        self.arglist = {}
        self.out = out
        self.modules = {}
        self.logfile = None
        self.buildtime = None
        self.buildname = None
        self.sqlite = False
        self.errors = []
        self.warnings = []

        # Default to outputing 'mach' style to stdout.
        log_args = {'log_mach': ['-']}
        if logfile:
            # If a logfile is requested we also output in a raw structured log
            # format to the requested file.
            log_args.update({'log_raw': [logfile]})

        self.logger = commandline.setup_logging("AwsyTest", log_args)

        # These can be passed to setup() like so:
        #   mytester.setup({'binary': 'blah', 'buildname': 'blee'})
        # OR you can call mytester.parseArgs() on a command-line formatted arg
        #   list (sys.argv) to extract them as needed.
        self.add_argument('-b', '--binary',
                          help='The binary (either in the current PATH or a full path) to test')
        self.add_argument('--buildname',
                          help='The name of this firefox build. If omitted, attempts to use the \
                                commit id from the mercurial respository the binary resides \
                                in')
        self.add_argument('--buildtime',
                          help='The unix timestamp to assign to this build \
                                build. If omitted, attempts to use the commit timestamp \
                                from the mercurial repository the binary resides in')
        self.add_argument('--test-module', '-m',
                          help='Load the specified test module (from libs). You must load at \
                                least one module to have tests',
                          action='append')
        self.add_argument('-l', '--logfile',
                          help='Log to given file')
        self.add_argument('-s', '--sqlitedb',
                          help='Merge datapoint into specified sqlite database')

        self.info("BenchTester instantiated")

    def add_argument(self, *args, **kwargs):
        act = self.argparser.add_argument(*args, **kwargs)
        if 'default' in kwargs:
            self.args[act.dest] = kwargs['default']

    # Parses commandline arguments, *AND* loads the modules specified on them,
    #   such that their arguments can be known/parsed. Does not prevent loading of
    #   more modules later on.
    # - returns a args dict suitable for passing to setup().
    # - If handle_exceptions is false, will let argparser failures fall through.
    #   Otherwise, prints an error.
    # - The "test_module" argument is returned, but not used by setup, and is
    #   useful for seeing what modules the commandline just caused to load
    def parse_args(self, rawargs=sys.argv[1:]):
        self.info("Parsing arguments...")
        try:
            args = vars(self.argparser.parse_known_args(rawargs)[0])
            # Modules can add more arguments, so load the ones specified
            # and re-parse
            if args['test_module']:
                for m in args['test_module']:
                    self.load_module(m)
            args = vars(self.argparser.parse_args(rawargs))
            return args
        except SystemExit, e:
            return False

    def __del__(self):
        # In case we exception out mid transaction or something
        if (hasattr(self, 'sqlite') and self.sqlite):
            self.sqlite.rollback()

    def _open_db(self):
        if not self.args['sqlitedb'] or self.sqlite:
            return True

        self.info("Setting up SQLite")
        if not self.buildname or not self.buildtime:
            self.error("Cannot use db without a buildname and buildtime set")
            self.sqlitedb = self.args['sqlitedb'] = None
            return False
        try:
            db_exists = os.path.exists(self.args['sqlitedb'])

            sql_path = os.path.abspath(self.args['sqlitedb'])
            self.sqlite = sqlite3.connect(sql_path, timeout=900)
            cur = self.sqlite.cursor()

            if db_exists:
                # make sure the version matches
                cur.execute(
                    "SELECT `version` FROM `benchtester_version` WHERE `version` = ?", [gVersion])
                row = cur.fetchone()
                version = row[0] if row else None
                if version != gVersion:
                    self.error("Incompatible versions: %s is version %s, current version is %s" % (
                        self.args['sqlitedb'], version, gVersion))
                    self.sqlitedb = self.args['sqlitedb'] = None
                    return False

            for schema in gTableSchemas:
                cur.execute(schema)

            if not db_exists:
                cur.execute(
                    "INSERT INTO `benchtester_version` (`version`) VALUES (?)", [gVersion])

            # Create/update the repo
            cur.execute(
                "SELECT `id` FROM `benchtester_repos` WHERE `name` = ?", [self.repo])
            row = cur.fetchone()
            if row:
                repo_id = int(row[0])
            else:
                cur.execute(
                    "INSERT INTO benchtester_repos(name) VALUES (?)", (self.repo, ))
                repo_id = cur.lastrowid

            # Create/update build ID
            cur.execute("SELECT `time`, `id` FROM `benchtester_builds` WHERE `name` = ?", [
                        self.buildname])
            buildrow = cur.fetchone()

            if buildrow and buildrow[0] != int(self.buildtime):
                self.warn("Build '%s' already exists in the database, but with a differing"
                          "timestamp. Overwriting old record (%s -> %s)" %
                          (self.buildname, buildrow[0], self.buildtime))
                cur.execute("UPDATE `benchtester_builds` SET `time` = ? WHERE `id` = ?", [
                            int(self.buildtime), buildrow[1]])
                self.build_id = buildrow[1]
            elif not buildrow:
                self.info("Creating new build record")
                cur.execute("INSERT INTO `benchtester_builds` (`name`, `time`, `repo_id`) "
                            "VALUES (?, ?, ?)",
                            (self.buildname, int(self.buildtime), repo_id))
                cur.execute("SELECT last_insert_rowid()")
                self.build_id = cur.fetchone()[0]
            else:
                self.build_id = buildrow[1]
                self.info("Found build record")
            self.sqlite.commit()
        except Exception, e:
            self.error(
                "Failed to setup sqliteDB '%s': %s - %s\n" % (self.args['sqlitedb'], type(e), e))
            self.sqlitedb = self.args['sqlitedb'] = None
            return False

        return True

    def setup(self, args):
        self.info("Performing setup")
        self.hg_ui = mercurial.ui.ui()

        # args will already contain defaults from add_argument calls
        self.args.update(args)

        # Check that binary is set
        if not self.args['binary']:
            return self.error("--binary is required, see --help")
        try:
            self.binary = os.path.abspath(self.args['binary'])
        except:
            self.binary = False
        if not self.binary or not os.path.exists(self.binary):
            return self.error("Unable to access binary '%s' (abs: '%s')\n" %
                              (self.args['binary'],
                               self.binary if self.binary else "Cannot resolve"))

        # Set commit name/timestamp
        if (self.args['buildname']):
            self.buildname = self.args['buildname'].strip()
        if (self.args['buildtime']):
            self.buildtime = str(self.args['buildtime']).strip()

        if 'repo' in self.args and self.args['repo']:
            self.repo = self.args['repo']
            self.info('Using provided repo: %s' % self.repo)
        else:
            self.repo = 'mozilla-inbound'
            self.info('Using default repo: mozilla-inbound')

        # Try to autodetect commitname/time if given a binary in a repo
        if not self.buildname or not self.buildtime:
            try:
                hg_repo = mercurial.hg.repository(
                    self.hg_ui, os.path.dirname(self.binary))
            except:
                hg_repo = None
            if hg_repo:
                try:
                    self.info(
                        "Binary is in a hg repo, attempting to detect build info")
                    self.hg_ui.pushbuffer()
                    mercurial.commands.tip(
                        self.hg_ui, hg_repo, template="{node} {date}")
                    tipinfo = self.hg_ui.popbuffer().split()
                    hg_changeset = tipinfo[0]
                    # Date is a float (truncate to int) of format
                    # 12345.0[+/-]3600 where 3600 is timezone info
                    hg_date = tipinfo[1].split('.')[0]
                    if not self.buildname:
                        self.buildname = hg_changeset
                        self.info(
                            "No build name given, using %s from repo binary is in" % self.buildname)
                    if not self.buildtime:
                        self.buildtime = hg_date
                        self.info(
                            "No build time given, using %s from repo binary is in" % self.buildtime)
                except Exception as e:
                    self.error("Found a Hg repo, but failed to get  changeset/timestamp. \
                      You may need to provide these manually with --buildname, --buildtime\
                      \nError was: %s" % (e))

        # Sanity checks
        if (self.sqlite):
            if (not self.buildname or not len(self.buildname)):
                self.error(
                    "Must provide a name for this build via --buildname in order to log to sqlite")
                return False

            try:
                inttime = int(self.buildtime, 10)
            except:
                inttime = None
            if (not inttime or str(inttime) != self.buildtime or inttime < 1):
                self.error(
                    "--buildtime must be set to a unix timestamp in order to log to sqlite")
                return False

        self.failed_modules = {}
        for m in self.modules:
            if not self.modules[m].setup():
                self.error("Failed to setup module %s!" % m)
                self.failed_modules[m] = self.modules[m]
        for m in self.failed_modules:
            del self.modules[m]

        self.ready = True
        self.info("Setup successful")
        return True
