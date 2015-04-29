#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys
import unittest
import urllib

from mozdownload.utils import urljoin

sys.path.insert(0, "../")
import mozhttpd_base_test as mhttpd


# Janky hack to work around not having modules setup
sys.path.insert(0, "../../benchtester")
from BuildGetter import TinderboxBuild, NightlyBuild, TryBuild, FTPBuild, list_tinderbox_builds

class BuildGetterTest(mhttpd.MozHttpdBaseTest):

  def test_list_tinderbox_builds(self):
    # expected: all builds
    builds = list_tinderbox_builds(base_url=self.wdir)
    self.assertEqual(builds, [1422727955, 1422727956, 1422730895, 1422731915])

    # expected: some builds
    builds = list_tinderbox_builds(starttime=1422730894, endtime=1422731915, base_url=self.wdir)
    self.assertEqual(builds, [1422730895, 1422731915])

    # expected: no builds
    builds = list_tinderbox_builds(starttime=1422731916, base_url=self.wdir)
    self.assertEqual(builds, [])

  def test_tinderbox(self):
    tinderbox_build = \
      TinderboxBuild(directory=self.temp_dir,
                     base_ftp_url=self.wdir,
                     base_hg_url=self.hgdir,
                     timestamp="1422727955")

    self.assertTrue(tinderbox_build.get_valid())
    self.assertEqual(tinderbox_build.get_tinderbox_timestamp(), 1422727955)
    self.assertEqual(tinderbox_build.get_branch(), "mozilla-inbound")

    tinderbox_build.prepare()

    binary = tinderbox_build.get_binary()
    self.assertTrue(os.path.exists(binary))
    self.assertEqual(tinderbox_build.get_revision(), "030744f8ef5a")
    self.assertEqual(tinderbox_build.get_buildtime(), 1422654729)
    self.assertEqual(tinderbox_build.get_tinderbox_timestamp(), 1422727955)

    tinderbox_build.cleanup()

    self.assertFalse(os.path.exists(binary))

    # Test a build that does not exist
    missing_build_dir = \
      TinderboxBuild(directory=self.temp_dir,
                     base_ftp_url=self.wdir,
                     base_hg_url=self.hgdir,
                     timestamp="1422727957")

    self.assertFalse(missing_build_dir.get_valid())

    # Test a build that started but does not have an archive
    missing_build_archive = \
      TinderboxBuild(directory=self.temp_dir,
                     base_ftp_url=self.wdir,
                     base_hg_url=self.hgdir,
                     timestamp="1422727956")

    self.assertFalse(missing_build_archive.get_valid())

  def test_nightly(self):
    nightly_build = \
      NightlyBuild(directory=self.temp_dir,
                   base_ftp_url=self.wdir,
                   base_hg_url=self.hgdir,
                   date="2015-01-31")

    self.assertTrue(nightly_build.get_valid())

    nightly_build.prepare()

    binary = nightly_build.get_binary()
    self.assertTrue(os.path.exists(binary))
    self.assertEqual(nightly_build.get_revision(), "d7e156a7a0a6")
    self.assertEqual(nightly_build.get_buildtime(), 1422654729)

    nightly_build.cleanup()

    self.assertFalse(os.path.exists(binary))

  def test_try(self):
    try_build = \
      TryBuild(directory=self.temp_dir,
               base_ftp_url=self.wdir,
               base_hg_url=self.hgdir,
               changeset="98567ca569b")

    self.assertTrue(try_build.get_valid())

    try_build.prepare()

    binary = try_build.get_binary()
    self.assertTrue(os.path.exists(binary))
    self.assertEqual(try_build.get_revision(), "798567ca569b")
    self.assertEqual(try_build.get_buildtime(), 1422654729)

    try_build.cleanup()

    self.assertFalse(os.path.exists(binary))

  def test_ftp(self):
    ftp_build = \
      FTPBuild(directory=self.temp_dir,
               base_ftp_url=self.wdir,
               base_hg_url=self.hgdir,
               path="%s/firefox/try-builds/erahm@mozilla.com-98567ca569b/"
                    "try-linux64/firefox-38.0a1.en-US.linux-x86_64.tar.bz2" % self.wdir)

    self.assertTrue(ftp_build.get_valid())

    ftp_build.prepare()

    binary = ftp_build.get_binary()
    self.assertTrue(os.path.exists(binary))
    self.assertEqual(ftp_build.get_revision(), "798567ca569b")
    self.assertEqual(ftp_build.get_buildtime(), 1422654729)

    ftp_build.cleanup()

    self.assertFalse(os.path.exists(binary))


if __name__ == '__main__':
  unittest.main()
