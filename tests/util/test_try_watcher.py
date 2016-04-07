#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys
import unittest
import urllib
import tempfile
import json

import mozfile

sys.path.insert(0, "util")
import try_watcher


class TryWatcherTest(unittest.TestCase):
    """Test for try_watcher utility functions."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        mozfile.remove(self.temp_dir)

    def test_sanitize_name(self):
        # test uppercase
        self.assertEqual(try_watcher.sanitize_name("MySeries"), "myseries")

        # test invalid characters
        for series in ("my-series", "my series", "my!series", "my#series"):
            self.assertEqual(try_watcher.sanitize_name(series), "my_series")

        self.assertEqual(try_watcher.sanitize_name("lots$of-invalid%chars"),
                         "lots_of_invalid_chars")

        # test invalid name
        self.assertIsNone(try_watcher.sanitize_name("areweslimyet_test"))

        # test valid name
        for series in ("this_is_valid", "series_2", "series123", "bug_12345"):
            self.assertEqual(try_watcher.sanitize_name(series), series)

    def test_write_try_job(self):
        revision = "dc44b0582aff3f33b783c3e96d09085bd979ba19"
        series = "test_series"

        try_watcher.write_try_job(revision, series, self.temp_dir)
        try_watcher.write_try_job(revision, series, self.temp_dir)
        try_watcher.write_try_job(revision, series, self.temp_dir)

        files = os.listdir(self.temp_dir)
        self.assertEqual(len(files), 3)

        expected = {
            'mode': 'try',
            'firstbuild': revision,
            'series': series,
            'prioritize': True
        }

        for file_name in files:
            self.assertTrue(file_name.endswith(".tryrequest"))
            with open(os.path.join(self.temp_dir, file_name), 'r') as f:
                actual = json.load(f)
                self.assertDictEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
