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
import time
import re
import shutil
import tarfile
import tempfile
import datetime
import json
import urllib2

import mozdownload

PUSHLOG_BRANCH_MAP = {
    'mozilla-inbound': 'integration/mozilla-inbound',
    'b2g-inbound': 'integration/b2g-inbound',
    'fx-team': 'integration/fx-team'
}

BASE_FTP_URL = 'https://archive.mozilla.org/pub'
BASE_HG_URL = 'https://hg.mozilla.org'

gDefaultBranch = 'mozilla-inbound'
gPushlogUrl = '%s/%s/json-pushes'
gTinderboxUrl = '%s/firefox/tinderbox-builds/%s-linux64/'
output = sys.stdout

# TODO
# This currently selects the linux-64 (non-pgo) build
# hardcoded at a few spots. This will need to be changed for non-linux testing


def _stat(msg):
    output.write("[BuildGetter] %s\n" % msg)


def get_build_info(url):
    """Retrieves the build info file and parses out relevant information"""
    # cross-platform FIXME, this is hardcoded to linux
    # trim off the extension, replace w/ .txt
    info_url = url[:-len(".tar.bz2")] + ".txt"

    try:
        raw = urllib2.urlopen(info_url, timeout=30).read()
    except (IOError, urllib2.URLError) as e:
        _stat("ERR: Failed to query server for %s %s %s" % (url, type(e), e))
        return None

    _stat("Got build info: %s" % raw)

    # This file has had lines changed in the past, just find a numeric line
    # and a url-of-revision-lookin' line
    m = re.search('^[0-9]{14}$', raw, re.MULTILINE)
    timestamp = int(time.mktime(time.strptime(m.group(0), '%Y%m%d%H%M%S')))
    m = re.search(
        '^https?://hg.mozilla.org/(.+)/rev/([0-9a-z]+)$', raw, re.MULTILINE)
    rev = m.group(2)
    branch = m.group(1)

    return (timestamp, rev, branch)


def pushlog_lookup(rev, branch=gDefaultBranch, base_url=BASE_HG_URL):
    """hg.m.o pushlog query"""
    pushlog_branch = PUSHLOG_BRANCH_MAP.get(branch, branch)
    pushlog = gPushlogUrl % (base_url, pushlog_branch)
    url = "%s?changeset=%s" % (pushlog, rev)
    try:
        raw = urllib2.urlopen(url, timeout=30).read()
    except (IOError, urllib2.URLError) as e:
        _stat("ERR: Failed to query pushlog for changeset %s on %s at %s: %s - %s" %
              (rev, branch, url, type(e), e))
        return False
    try:
        pushlog = json.loads(raw)
        if len(pushlog) != 1:
            raise ValueError(
                "Pushlog returned %u items, expected 1" % len(pushlog))
        for cset in pushlog[pushlog.keys()[0]]['changesets']:
            if cset.startswith(rev):
                break
        else:
            raise ValueError(
                "Pushlog returned a push that does not contain this revision?")

    except ValueError as e:
        _stat("ERR: pushlog returned invalid JSON for changeset %s\n"
              "  Error was:\n    %s - %s\n  JSON:\     %s" %
              (rev, type(e), e, raw))
        return False

    push = pushlog[pushlog.keys()[0]]
    _stat("For rev %s on branch %s got push by %s at %u with %u changesets" %
          (cset, branch, push['user'], push['date'], len(push['changesets'])))
    return cset, push['date']


def list_tinderbox_builds(starttime=0, endtime=int(time.time()),
                          branch=gDefaultBranch, base_url=BASE_FTP_URL):
    """
    Gets a list of TinderboxBuild objects for all builds on ftp.m.o within
    specified date range.
    """
    parser = mozdownload.parser.DirectoryParser(
        gTinderboxUrl % (base_url, branch))
    entries = parser.filter(r'^\d+$')  # only entries that are all digits
    return sorted([int(x) for x in entries if int(x) >= starttime and int(x) <= endtime])


class Build():
    """Abstract base class for builds."""

    def prepare(self):
        """Downloads or builds and extracts the build to a temporary directory"""
        raise NotImplementedError()

    def cleanup(self):
        raise NotImplementedError()

    def get_revision(self):
        raise NotImplementedError()

    def get_buildtime(self):
        raise NotImplementedError()

    def get_valid(self):
        raise NotImplementedError()

    def get_binary(self):
        """Requires prepare()'d"""
        raise NotImplementedError()


class DownloadedBuild(Build):
    """Base class with shared helpers for Tinderbox, Nightly, and Try builds"""

    def __init__(self, scraper_args, directory=None,
                 base_ftp_url=BASE_FTP_URL, base_hg_url=BASE_HG_URL):
        """
        Sets up the build for downloading.

        Creates a mozdownloader.scraper instance and then queries the server for
        more build details such as revision, branch, and timestamp.

        :param scraper_args: Specifies the |mozdownload.scraper| type to use and
          arguments that should be passed to it. Format:
          { 'type': <class_type>, 'args': { ... } }
        """

        self._branch = None
        self._extracted = directory
        self._cleanup_dir = False
        self._prepared = False
        self._revision = None
        self._scraper = None
        self._scraperTarget = None
        self._timestamp = None
        self._valid = False
        self._base_ftp_url = base_ftp_url
        self._base_hg_url = base_hg_url

        if not directory:
            self._extracted = tempfile.mkdtemp("BuildGetter_firefox")
            self._cleanup_dir = True

        # FIXME: platform hard coded to linux64
        default_args = {
            'destination': self._extracted,
            'platform': 'linux64',
            'base_url': base_ftp_url,
        }

        default_args.update(scraper_args['args'])

        # cache scraper details to support serialization
        self._scraper_type = scraper_args['type']
        self._scraper_args = default_args

        try:
            self._scraper = scraper_args['type'](**default_args)
            url = self._scraper.url
        except mozdownload.errors.NotFoundError:
            _stat("ERR: Build not found")
            return

        ret = get_build_info(url)
        if not ret:
            _stat("ERR: Failed to lookup information about the build")
            return

        (self._timestamp, self._revision, self._branch) = ret

        ret = pushlog_lookup(self._revision, self._branch, self._base_hg_url)
        if not ret:
            _stat("ERR: Failed to lookup the build in the pushlog")
            return

        (self._revision, self._timestamp) = ret

        self._valid = True

    @staticmethod
    def extract_build(src, dstdir):
        """Extracts the given build to the given directory."""

        # cross-platform FIXME, this is hardcoded to tar at the moment
        with tarfile.open(src, mode='r:*') as tar:
            tar.extractall(path=dstdir)

    def prepare(self):
        """
        Prepares the build for testing.

        Downloads the build and extracts it to a temporary directory.
        """

        if not self._scraper:
            # recreate it
            self._scraper = self._scraper_type(**self._scraper_args)

        if not self._valid:
            raise Exception("Attempted to prepare() invalid build")

        self._scraper.download()
        self._scraperTarget = self._scraper.filename

        _stat("Extracting build")
        self.extract_build(self._scraper.filename, self._extracted)

        self._prepared = True
        self._scraper = None
        return True

    def cleanup(self):
        if self._prepared:
            self._prepared = False

            # remove the downloaded archive
            os.remove(self._scraperTarget)

            # remove the extracted archive
            shutil.rmtree(os.path.join(self._extracted, "firefox"))

        # remove the temp directory that was created
        if self._cleanup_dir:
            shutil.rmtree(self._extracted)

        return True

    def get_revision(self):
        return self._revision

    def get_valid(self):
        return self._valid

    def get_binary(self):
        if not self._prepared:
            raise Exception("Build is not prepared")
        # FIXME More hard-coded linux stuff
        return os.path.join(self._extracted, "firefox", "firefox")

    def get_buildtime(self):
        return self._timestamp


class CompileBuild(Build):
    """
    A build that needs to be compiled

    This is currently unsupported, see:
      https://github.com/mozilla/areweslimyet/issues/47
    """
    pass


class FTPBuild(DownloadedBuild):
    """A build that simply points to a full path on ftp.m.o"""

    def __init__(self, path, *args, **kwargs):
        self._path = path
        scraper_info = {
            'type': mozdownload.DirectScraper,
            'args': {'url': path}
        }

        DownloadedBuild.__init__(self, scraper_info, *args, **kwargs)


class TryBuild(DownloadedBuild):
    """A try build from ftp.m.o. Initialized with a 12-digit try changeset."""

    def __init__(self, changeset, *args, **kwargs):
        # mozdownload requires the full revision, look it up if necessary.
        if len(changeset) != 40:
            (changeset, _) = pushlog_lookup(changeset, branch='try',
                                            base_url=kwargs.get('base_hg_url', BASE_HG_URL))

        self._changeset = changeset
        scraper_info = {
            'type': mozdownload.scraper.TryScraper,
            'args': {'revision': changeset}
        }

        DownloadedBuild.__init__(self, scraper_info, *args, **kwargs)


class NightlyBuild(DownloadedBuild):
    """A nightly build. Initialized with a date() object or a YYYY-MM-DD string"""

    def __init__(self, date, *args, **kwargs):
        self._date = date if isinstance(
            date, datetime.date) else datetime.datetime.strptime(date, "%Y-%m-%d")
        scraper_info = {
            'type': mozdownload.scraper.DailyScraper,
            'args': {'date': self._date.strftime("%Y-%m-%d")}
        }

        DownloadedBuild.__init__(self, scraper_info, *args, **kwargs)


class TinderboxBuild(DownloadedBuild):
    """A tinderbox build from ftp.m.o. Initialized with a timestamp to build"""

    def __init__(self, timestamp, branch="mozilla-inbound", *args, **kwargs):
        if not branch:
            branch = "mozilla-inbound"

        self._branch_name = branch
        self._tinderbox_timestamp = int(timestamp)

        # Use this as the timestamp if finding the build fails
        self._timestamp = self._tinderbox_timestamp

        scraper_info = {
            'type': mozdownload.scraper.TinderboxScraper,
            'args': {'branch': branch, 'date': str(self._tinderbox_timestamp)}
        }

        DownloadedBuild.__init__(self, scraper_info, *args, **kwargs)

    def get_tinderbox_timestamp(self):
        return self._tinderbox_timestamp

    def get_branch(self):
        return self._branch_name
