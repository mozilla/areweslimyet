#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2012 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

# Helpers for building/testing many builds from either ftp.m.o nightly/tinderbox,
# or via autobuild

import os
import sys
import ftplib
import time
import re
import socket
import cStringIO
import shutil
import tarfile
import tempfile
import datetime
import subprocess
import json
import urllib
import urllib2

gDefaultBranch = 'integration/mozilla-inbound'
gPushlog = 'https://hg.mozilla.org/%s/json-pushes'
output = sys.stdout

# TODO
# This currently selects the linux-64 (non-pgo) build
# hardcoded at a few spots. This will need to be changed for non-linux testing

def _stat(msg):
  output.write("[BuildGetter] %s\n" % msg);

##
## Utility
##

def _subprocess(environment, command, cwd, logfile):
  newenv = os.environ.copy()
  newenv.update(environment)
  _stat("Running command \"%s\" in \"%s\" with env \"%s\"" % (command, cwd, environment))

  proc = subprocess.Popen(command,
                          env=newenv,
                          cwd=cwd,
                          stderr=subprocess.STDOUT,
                          stdout=subprocess.PIPE)

  # Wait for EOF, logging if desired
  while True:
    data = proc.stdout.read(1024)
    if not data: break
    if logfile:
      logfile.write(data)

  return proc.wait()

# Given a firefox build file handle, extract it to a temp directory, return that
def _extract_build(fileobject):
  # cross-platform FIXME, this is hardcoded to .tar.bz2 at the moment
  ret = tempfile.mkdtemp("BuildGetter_firefox")
  tar = tarfile.open(fileobj=fileobject, mode='r:bz2')
  tar.extractall(path=ret)
  tar.close()
  return ret

##
## hg.m.o pushlog query
##

def pushlog_lookup(rev, branch = gDefaultBranch):
  pushlog = gPushlog % (branch,)
  try:
    raw = urllib2.urlopen("%s?changeset=%s" % (pushlog, rev), timeout=30).read()
  except (IOError, urllib2.URLError) as e:
    _stat("ERR: Failed to query pushlog for changeset %s on %s: %s - %s" % (rev, branch, type(e), e))
    return False
  try:
    pushlog = json.loads(raw)
    if len(pushlog) != 1:
      raise ValueError("Pushlog returned %u items, expected 1" % len(pushlog))
    for cset in pushlog[pushlog.keys()[0]]['changesets']:
      if cset.startswith(rev):
        break
    else:
      raise ValueError("Pushlog returned a push that does not contain this revision?")

  except ValueError as e:
    _stat("ERR: pushlog returned invalid JSON for changeset %s\n  Error was:\n    %s - %s\n  JSON:\     %s" % (rev, type(e), e, raw))
    return False

  push = pushlog[pushlog.keys()[0]]
  _stat("For rev %s on branch %s got push by %s at %u with %u changesets" % (cset, branch, push['user'], push['date'], len(push['changesets'])))
  return cset, push['date']

##
## Working with ftp.m.o
##

ftp = None
def ftp_open():
  global ftp
  try:
    ftp.voidcmd('CWD /')
  except:
    if ftp: ftp.close()
    _stat("Opening new FTP connection")
    ftp = ftplib.FTP('ftp.mozilla.org')
    ftp.login()

  return ftp

def ftp_find_try_rev(rev):
  ftp = ftp_open()

  try:
    ftp.voidcmd('CWD /pub/mozilla.org/firefox/try-builds')
  except:
    _stat("Could not find try directory")
    return None

  found = []
  def findrev(line):
    if line.endswith(rev[0:12]):
      found.append(line)

  try:
    ftp.retrlines('NLST', findrev)
  except:
    _stat("Failed to list try directory")
    return

  if not len(found):
    _stat("Could not find a try folder matching %s" % (rev,))
    return None

  try:
    ftp.voidcmd('CWD %s/try-linux64' % found[0])
  except:
    _stat("Folder %s does not contain a linux64 build")
    return None

  return "/pub/mozilla.org/firefox/try-builds/%s/try-linux64" % found[0]

# Reads a file, returns the blob
def _ftp_get(ftp, filename):
  # (We use readfile.filedat temporarily because of py2's lack of proper scoping
  #  for nested functions)
  def readfile(line):
      readfile.filedat.write(line)

  # Python2 didn't have any design flaws. None, I say!
  readfile.filedat = cStringIO.StringIO()

  try:
    ftp.retrbinary('RETR %s' % filename, readfile)
  except:
    return False

  readfile.filedat.seek(0)
  return readfile.filedat

# Returns false if there's no linux-64 build here,
# otherwise returns a tuple of (timestamp, revision, filename)
def _ftp_check_build_dir(ftp, dirname):
  global infofile
  _stat("Checking directory %s" % dirname)
  infofile = False
  def findinfofile(line):
    global infofile
    if line.startswith('firefox') and line.endswith('linux-x86_64.txt'):
      infofile = line

  try:
    ftp.voidcmd('CWD %s' % dirname)
  except:
    return False

  ftp.retrlines('NLST', findinfofile)
  if not infofile:
    ftp.voidcmd('CwD ..')
    return False

  #
  # read and parse info file
  #

  fileio = _ftp_get(ftp, infofile)
  if not fileio:
    return False
  filedat = fileio.getvalue()
  fileio.close()

  _stat("Got build info: %s" % filedat)

  # This file has had lines changed in the past, just find a numeric line
  # and a url-of-revision-lookin' line
  m = re.search('^[0-9]{14}$', filedat, re.MULTILINE)
  timestamp = int(time.mktime(time.strptime(m.group(0), '%Y%m%d%H%M%S')))
  m = re.search('^https?://hg.mozilla.org/(.+)/rev/([0-9a-z]{12})$', filedat, re.MULTILINE)
  rev = m.group(2)
  branch = m.group(1)
  nightlyfile = infofile[:-4] + ".tar.bz2"

  return (timestamp, rev, branch, nightlyfile)

# Returns a list of commit IDs between two revisions, inclusive. If pullfirst is
# set, pull before checking
def get_hg_range(repodir, firstcommit, lastcommit, pullfirst=False):
    # Setup Hg
    import mercurial, mercurial.ui, mercurial.hg, mercurial.commands
    hg_ui = mercurial.ui.ui()
    repo = mercurial.hg.repository(hg_ui, repodir)
    hg_ui.readconfig(os.path.join(repodir, ".hg", "hgrc"))

    # Pull
    if pullfirst:
      hg_ui.pushbuffer()
      mercurial.commands.pull(hg_ui, repo, update=True, check=True)
      result = hg_ui.popbuffer()

    # Get revisions
    hg_ui.pushbuffer()
    try:
      mercurial.commands.log(hg_ui, repo, rev=[ "%s:%s" % (firstcommit, lastcommit) ], template="{node} ", date="", user=None, follow=None)
      return hg_ui.popbuffer().split(' ')[:-1]
    except:
      # mercurial throws all kinds of fun exceptions for bad input
      return False

# Gets a list of TinderboxBuild objects for all builds on ftp.m.o within
# specified date range
def list_tinderbox_builds(starttime = 0, endtime = int(time.time()), branch = gDefaultBranch):
  ftp = ftp_open()
  ftp.voidcmd('CWD /pub/firefox/tinderbox-builds/%s-linux64/' % (branch.split('/')[-1],))

  def get(line):
    try:
      x = int(line)
      if x >= starttime and x <= endtime:
        get.ret.append(x)
    except: pass
  get.ret = []
  ftp.retrlines('NLST', get)

  get.ret.sort()

  return get.ret

#
# Build classes
#

# Abstract base class
class Build():
  # Downloads or builds and extracts the build to a temporary directory
  def prepare(self):
    raise Exception("Attempt to call method on abstract base class")
  def cleanup(self):
    raise Exception("Attempt to call method on abstract base class")
  def get_revision(self):
    raise Exception("Attempt to call method on abstract base class")
  def get_buildtime(self):
    raise Exception("Attempt to call method on abstract base class")
  def get_valid(self):
    raise Exception("Attempt to call method on abstract base class")
  # Requires prepare()'d
  def get_binary(self):
    raise Exception("Attempt to call method on abstract base class")

# Abstract class with shared helpers for TinderboxBuild/NightlyBuild
class BaseFTPBuild(Build):
  def prepare(self):
    if not self._valid:
      raise Exception("Attempted to prepare() invalid build")
    if not self._revision or not self._timestamp:
      raise Exception("Valid build lacks revision/timestamp?")

    ftp = ftp_open()

    ftpfile = _ftp_get(ftp, self._filename)
    if not ftpfile:
      _stat("Failed to download build from FTP")
      return False

    _stat("Extracting build")
    self._extracted = _extract_build(ftpfile)
    ftpfile.close()
    self._prepared = True
    return True

  def cleanup(self):
    if self._prepared:
      self._prepared = False
      shutil.rmtree(self._extracted)
    return True

  def get_revision(self):
    return self._revision

  def get_binary(self):
    if not self._prepared:
      raise Exception("Build is not prepared")
    # FIXME More hard-coded linux stuff
    return os.path.join(self._extracted, "firefox", "firefox")

  def get_buildtime(self):
    return self._timestamp

  def get_valid(self):
    return self._valid

# A build that needs to be compiled
# This is currently unsupported, see:
# https://github.com/mozilla/areweslimyet/issues/47
class CompileBuild(Build):
  pass

# A build that simply points to a FTP directory on ftp.m.o
# TODO currently we just hard-code 64bit-linux builds...
class FTPBuild(BaseFTPBuild):
  def __init__(self, path):
    self._prepared = False
    self._path = path
    self._valid = False
    self._timestamp = None

    if path.startswith("try:"):
      self._path = ftp_find_try_rev(path[4:])
      if not self._path:
        _stat("Failed to find try revision %s" % path[4:])
        return

    _stat("Checking for linux-64 build at %s" % (self._path,))

    ftp = ftp_open()
    try:
      ftp.voidcmd('CWD %s' % self._path)
    except:
      _stat("Could not change to directory %s" % self._path)
      return

    ret = _ftp_check_build_dir(ftp, self._path)
    if not ret:
      _stat("No linux64 build found")
      return

    (timestamp, self._revision, branch, filename) = ret
    ret = pushlog_lookup(self._revision, branch)
    if not ret:
      _stat("ERR: Pushlog lookup failed for %s on %s" % (self._revision, branch))
      return
    (self._revision, self._timestamp) = ret
    self._filename = "%s/%s" % (self._path, filename)
    self._valid = True

# a nightly build. Initialized with a date() object or a YYYY-MM-DD string
class NightlyBuild(BaseFTPBuild):
  def __init__(self, date):
    self._prepared = False
    self._date = date
    self._timestamp = None
    self._revision = None
    self._valid = False
    month = self._date.month
    day = self._date.day
    year = self._date.year
    _stat("Looking up nightly for %s/%s, %s" % (month, day, year))

    # Connect, CD to this month's dir
    ftp = ftp_open()
    nightlydir = 'pub/firefox/nightly/%i/%02i' % (year, month)
    try:
      ftp.voidcmd('CWD %s' % nightlydir)
    except Exception, e:
      _stat("Failed to enter the directory for this nightly")
      return;

    # Find the appropriate YYYY-MM-DD-??-mozilla-central directory. There may be
    # multiple if the builds took over an hour
    nightlydirs = []
    def findnightlydir(line):
      x = line.split('-')
      if x[-2:] == [ 'mozilla', 'central' ] and int(x[0]) == year and int(x[1]) == month and int(x[2]) == day:
        nightlydirs.append(line)

    rawlist = ftp.retrlines('NLST', findnightlydir)

    if not len(nightlydirs):
      return;

    _stat("Nightly directories are: %s" % ', '.join(nightlydirs))

    for x in nightlydirs:
      ret = _ftp_check_build_dir(ftp, x)
      if ret:
        (self._timestamp, self._revision, _, filename) = ret
        self._filename = "%s/%s/%s" % (nightlydir, x, filename)
        break

    if not ret:
      _stat("ERR: Failed to find directory containing this nightly")
      return

    ret = pushlog_lookup(self._revision)
    if not ret:
      _stat("ERR: Failed to lookup this nightly in the pushlog")
      return

    (self._revision, self._timestamp) = ret
    self._valid = True

# A tinderbox build from ftp.m.o. Initialized with a timestamp to build
class TinderboxBuild(BaseFTPBuild):
  def __init__(self, timestamp, branch = gDefaultBranch):
    timestamp = int(timestamp)
    self._tinderbox_timestamp = timestamp
    self._prepared = False
    self._revision = None
    # Use this as the timestamp if finding the build fails
    self._timestamp = self._tinderbox_timestamp
    self._branch = branch
    self._valid = False

    # FIXME hardcoded linux stuff
    basedir = "/pub/firefox/tinderbox-builds/%s-linux64" % (branch.split('/')[-1],)
    ftp = ftp_open()
    ftp.voidcmd('CWD %s' % (basedir,))
    ret = _ftp_check_build_dir(ftp, timestamp)
    if not ret:
      _stat("WARN: Tinderbox build %s was not found" % (timestamp,))
      return
    (timestamp, self._revision, _, filename) = ret

    self._filename = "%s/%s/%s" % (basedir, self._tinderbox_timestamp, filename)
    ret = pushlog_lookup(self._revision)
    if not ret:
      _stat("Failed to lookup this tinderbox build in the pushlog")
      return
    (self._revision, self._timestamp) = ret
    self._valid = True

  def get_tinderbox_timestamp(self):
    return self._tinderbox_timestamp

  def get_branch(self):
    return self._branch
