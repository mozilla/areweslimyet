#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2012 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import os
import argparse
import sqlite3
import subprocess
import mercurial, mercurial.ui, mercurial.hg, mercurial.commands
import time

gTableSchemas = [
  # Builds - info on builds we have tests for
  '''CREATE TABLE IF NOT EXISTS
      "benchtester_builds" ("id" INTEGER PRIMARY KEY NOT NULL,
                           "name" VARCHAR NOT NULL UNIQUE,
                           "time" DATETIME NOT NULL)''',

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

  # Data - datapoints from tests
  '''CREATE TABLE IF NOT EXISTS
      "benchtester_data" ("test_id" INTEGER NOT NULL,
                          "datapoint_id" INTEGER NOT NULL,
                          "value" INTEGER NOT NULL,
                          "meta" VARCHAR)''',

  # Some default indexes
  '''CREATE INDEX IF NOT EXISTS test_lookup ON benchtester_tests ( name, build_id DESC )''',
  '''CREATE INDEX IF NOT EXISTS data_for_test ON benchtester_data ( test_id DESC, datapoint_id )'''
];

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
    self.log('info', msg)

  def error(self, msg):
    self.errors.append(msg)
    self.log('error', msg)
    return False

  def warn(self, msg):
    self.warnings.append(msg)
    self.log('warning', msg)

  def log(self, type, msg, timestamp = None, noprint = False):
    if not timestamp:
      timestamp = time.clock() - self.starttime

    if self.logfile:
      self.logfile.write("%.2f :: %s :: %s\n" % (timestamp, type.upper(), msg))
      self.logfile.flush()
    elif not self.ready:
      # Cache lines until setup is called to open the logfile
      if not hasattr(self, 'logcache'): self.logcache = []
      self.logcache.append((type, msg, timestamp))

    if not noprint:
      self.out.write("[%.2f] %s: %s\n" % (timestamp, type.upper(), msg))

  def run_test(self, testname, testtype, testvars={}):
    if not self.ready:
      return self.error("run_test() called before setup")

    # make sure a record is created, even if no testdata is produced
    if not self._open_db():
      return self.error("Failed to open sqlite database")

    if self.modules.has_key(testtype):
      self.info("Passing test '%s' to module '%s'" % (testname, testtype))
      return self.modules[testtype].run_test(testname, testvars)
    else:
      return self.error("Test '%s' is of unknown type '%s'" % (testname, testtype))

  # Modules are named 'SomeModule.py' and have a class named 'SomeModule' based on BenchTest
  def load_module(self, modname):
    if self.ready:
      return self.error("Modules must be loaded before setup()")

    if self.modules.has_key(modname): return True

    self.info("Loading module '%s'" % (modname))
    try:
      module = __import__(modname)
      self.modules[modname] = vars(module)[modname](self)
    except Exception, e:
      return self.error("Failed to load module '%s', Exception '%s': %s" % (modname, type(e), e))

    return True

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

    #for datapoint, val in datapoints.iteritems():
    #  self.info("Datapoint: Test '%s', Datapoint '%s', Value '%s'" % (testname, datapoint, val))
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
          insertbegin = time.time()
          self.info("Inserting %u datapoints into DB" % len(datapoints))
          cur.executemany("INSERT OR IGNORE INTO `benchtester_datapoints`(name) "
                          "VALUES (?)",
                          ([ datapoint[0] ] for datapoint in datapoints))
          self.sqlite.commit()
          self.info("Filled datapoint names in %.02fs" % (time.time() - insertbegin))
          insertbegin = time.time()
          # If val is a list, it is interpreted as [ value, meta ]
          cur.executemany("INSERT INTO `benchtester_data` "
                          "SELECT ?, p.id, ?, ? FROM `benchtester_datapoints` p "
                          "WHERE p.name = ?",
                          ( [ testid,
                              dp[1],
                              dp[2] if len(dp) > 2 else None,
                              dp[0] ]
                            for dp in datapoints ))
          self.sqlite.commit()
          self.info("Filled datapoint values in %.02fs" % (time.time() - insertbegin))
      except Exception, e:
        self.error("Failed to insert data into sqlite, got '%s': %s" % (type(e), e))
        self.sqlite.rollback()
        return False
    return True

  def __init__(self, out=sys.stdout):
    self.starttime = time.clock()
    self.ready = False
    self.args = {}
    self.argparser = argparse.ArgumentParser(description='Run automated benchmark suite, optionally adding datapoints to a sqlite database')
    self.arglist = {}
    self.out = out
    self.modules = {}
    self.logfile = None
    self.buildtime = None
    self.buildname = None
    self.sqlite = False
    self.errors = []
    self.warnings = []

    # These can be passed to setup() like so:
    #   mytester.setup({'binary': 'blah', 'buildname': 'blee'})
    # OR you can call mytester.parseArgs() on a command-line formatted arg list (sys.argv) to extract
    #   them as needed.
    self.add_argument('-b', '--binary',              help='The binary (either in the current PATH or a full path) to test')
    self.add_argument('--buildname',                 help='The name of this firefox build. If omitted, attempts to use the \
                                                           commit id from the mercurial respository the binary resides \
                                                           in')
    self.add_argument('--buildtime',                 help='The unix timestamp to assign to this build \
                                                           build. If omitted, attempts to use the commit timestamp \
                                                           from the mercurial repository the binary resides in')
    self.add_argument('--test-module', '-m',         help='Load the specified test module (from libs). You must load at least one module to have tests',
                                                     action='append')
    self.add_argument('-l', '--logfile',             help='Log to given file')
    self.add_argument('-s', '--sqlitedb',            help='Merge datapoint into specified sqlite database')

    self.info("BenchTester instantiated")

  def add_argument(self, *args, **kwargs):
    act = self.argparser.add_argument(*args, **kwargs)
    if kwargs.has_key('default'):
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
    if not self.args['sqlitedb'] or self.sqlite: return True

    self.info("Setting up SQLite")
    if not self.buildname or not self.buildtime:
      self.error("Cannot use db without a buildname and buildtime set")
      self.sqlitedb = self.args['sqlitedb'] = None
      return False
    try:
      sql_path = os.path.abspath(self.args['sqlitedb'])
      self.sqlite = sqlite3.connect(sql_path, timeout=900)
      cur = self.sqlite.cursor()
      for schema in gTableSchemas:
        cur.execute(schema)
      # Create/update build ID
      cur.execute("SELECT `time`, `id` FROM `benchtester_builds` WHERE `name` = ?", [ self.buildname ])
      buildrow = cur.fetchone()

      if buildrow and buildrow[0] != int(self.buildtime):
        self.warn("Build '%s' already exists in the database, but with a differing timestamp. Overwriting old record (%s -> %s)" % (self.buildname, buildrow[0], self.buildtime))
        cur.execute("UPDATE `benchtester_builds` SET `time` = ? WHERE `id` = ?", [ int(self.buildtime), buildrow[1] ])
        self.build_id = buildrow[1]
      elif not buildrow:
        self.info("Creating new build record")
        cur.execute("INSERT INTO `benchtester_builds` (`name`, `time`) VALUES (?, ?)", (self.buildname, int(self.buildtime)))
        cur.execute("SELECT last_insert_rowid()")
        self.build_id = cur.fetchone()[0]
      else:
        self.build_id = buildrow[1]
        self.info("Found build record")
      self.sqlite.commit()
    except Exception, e:
      self.error("Failed to setup sqliteDB '%s': %s - %s\n" % (self.args['sqlitedb'], type(e), e))
      self.sqlitedb = self.args['sqlitedb'] = None
      return False

    return True

  def setup(self, args):
    self.info("Performing setup")
    self.hg_ui = mercurial.ui.ui()

    # args will already contain defaults from add_argument calls
    self.args.update(args)

    # Open logfile
    if self.args['logfile']:
      self.logfile_path = None
      try:
        self.logfile_path = os.path.abspath(self.args['logfile'])
        self.logfile = open(self.logfile_path, 'w')
      except Exception, e:
        return self.error("Unable to open logfile '%s' (%s)" % (self.args['logfile'], self.logfile_path))
      # Print any lines that occured before the logfile opened
      if hasattr(self, 'logcache'):
        self.logcache.reverse()
        while len(self.logcache):
          time, msg, timestamp = self.logcache.pop()
          self.log(time, msg, timestamp, True)
        self.logcache = None
    self.info("Opened logfile")

    # Check that binary is set
    if not self.args['binary']:
      return self.error("--binary is required, see --help")
    try:
      self.binary = os.path.abspath(self.args['binary'])
    except:
      self.binary = False
    if not self.binary or not os.path.exists(self.binary):
      return self.error("Unable to access binary '%s' (abs: '%s')\n" % (self.args['binary'], self.binary if self.binary else "Cannot resolve"))

    # Set commit name/timestamp
    if (self.args['buildname']):
      self.buildname = self.args['buildname'].strip()
    if (self.args['buildtime']):
      self.buildtime = str(self.args['buildtime']).strip()


    # Try to autodetect commitname/time if given a binary in a repo
    if not self.buildname or not self.buildtime:
      try:
        hg_repo = mercurial.hg.repository(self.hg_ui, os.path.dirname(self.binary))
      except:
        hg_repo = None
      if hg_repo:
        try:
          self.info("Binary is in a hg repo, attempting to detect build info")
          self.hg_ui.pushbuffer()
          mercurial.commands.tip(self.hg_ui, hg_repo, template="{node} {date}")
          tipinfo = self.hg_ui.popbuffer().split()
          hg_changeset = tipinfo[0]
          # Date is a float (truncate to int) of format 12345.0[+/-]3600 where 3600 is timezone info
          hg_date = tipinfo[1].split('.')[0]
          if not self.buildname:
            self.buildname = hg_changeset
            self.info("No build name given, using %s from repo binary is in" % self.buildname)
          if not self.buildtime:
            self.buildtime = hg_date
            self.info("No build time given, using %s from repo binary is in" % self.buildtime)
        except Exception as e:
          self.error("Found a Hg repo, but failed to get  changeset/timestamp. \
                      You may need to provide these manually with --buildname, --buildtime\
                      \nError was: %s" % (e));

    # Sanity checks
    if (self.sqlite):
      if (not self.buildname or not len(self.buildname)):
        self.error("Must provide a name for this build via --buildname in order to log to sqlite")
        return False

      try:
        inttime = int(self.buildtime, 10)
      except:
        inttime = None
      if (not inttime or str(inttime) != self.buildtime or inttime < 1):
        self.error("--buildtime must be set to a unix timestamp in order to log to sqlite")
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
