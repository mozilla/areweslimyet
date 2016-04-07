#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import unittest

from benchtester.BenchTester import BenchTester

class BenchTesterTest(unittest.TestCase):

  def test_process_name_mapping(self):
    # Test one w/ pid, one w/o
    proc_names_list = [
        "Main",
        "Web Content (1234)"
        ]

    expected_mappings = {
        "Main": "Main",
        "Web Content (1234)": "Web Content"
        }

    proc_name_mappings = BenchTester.map_process_names(proc_names_list)
    self.assertEqual(expected_mappings, proc_name_mappings)

    # Test multiple of one type
    proc_names_list = [
        "Main",
        "Web Content (1234)",
        "Web Content (2345)",
        "Web Content (3456)"
        ]

    expected_mappings = {
        "Main": "Main",
        "Web Content (1234)": "Web Content",
        "Web Content (2345)": "Web Content 2",
        "Web Content (3456)": "Web Content 3"
        }

    proc_name_mappings = BenchTester.map_process_names(proc_names_list)
    self.assertEqual(expected_mappings, proc_name_mappings)

    # Test multiple of one type with pid prefix
    proc_names_list = [
        "Main",
        "Web Content (pid 1234)",
        "Web Content (pid 2345)",
        "Web Content (pid 3456)"
        ]

    expected_mappings = {
        "Main": "Main",
        "Web Content (pid 1234)": "Web Content",
        "Web Content (pid 2345)": "Web Content 2",
        "Web Content (pid 3456)": "Web Content 3"
        }

    proc_name_mappings = BenchTester.map_process_names(proc_names_list)
    self.assertEqual(expected_mappings, proc_name_mappings)


    # Test multiple of several types
    proc_names_list = [
        "Main",
        "Web Content (1234)",
        "Web Content (2345)",
        "Web Content (3456)",
        "GMP (1234)",
        "GMP (2345)"
        ]

    expected_mappings = {
        "Main": "Main",
        "Web Content (1234)": "Web Content",
        "Web Content (2345)": "Web Content 2",
        "Web Content (3456)": "Web Content 3",
        "GMP (1234)": "GMP",
        "GMP (2345)": "GMP 2"
        }

    proc_name_mappings = BenchTester.map_process_names(proc_names_list)
    self.assertEqual(expected_mappings, proc_name_mappings)

    # Test with a dictionary
    proc_names_dict = {
        "Main": [],
        "Web Content (1234)": [],
        "Web Content (2345)": [],
        "Web Content (3456)": [],
        "GMP (1234)": [],
        "GMP (2345)": []
        }

    # We can't guarantee the order of the entries in the dictionary so we just
    # verify the write values are present.
    expected_values = [
        "Main",
        "Web Content",
        "Web Content 2",
        "Web Content 3",
        "GMP",
        "GMP 2"
        ]

    proc_name_mappings = BenchTester.map_process_names(proc_names_dict)
    self.assertEqual(sorted(expected_values), sorted(proc_name_mappings.values()))

    # Test with different pid orderings
    proc_names_list = [
        "Main",
        "Web Content (2345)",
        "Web Content (1234)",
        "Web Content (3456)",
        "GMP (2345)",
        "GMP (1234)"
        ]

    expected_mappings = {
        "Main": "Main",
        "Web Content (2345)": "Web Content",
        "Web Content (1234)": "Web Content 2",
        "Web Content (3456)": "Web Content 3",
        "GMP (2345)": "GMP",
        "GMP (1234)": "GMP 2"
        }

    proc_name_mappings = BenchTester.map_process_names(proc_names_list)
    self.assertEqual(expected_mappings, proc_name_mappings)


if __name__ == '__main__':
  unittest.main()
