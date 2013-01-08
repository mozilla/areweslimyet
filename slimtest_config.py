#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2012 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

# Tests for areweslimyet.com. Used by run_slimtest.py or slimtest_batchtester_hook.py

AreWeSlimYetTests = {
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
  ## We also ran tests without a delay for a while, but they produce fairly
  ## useless data
  ##
  # "Slimtest-TalosTP5":
  # {
  #   'type': "EnduranceTest",
  #   'vars':
  #     {
  #       'test': [ 'mozmill_endurance_test' ],
  #       'entities': 100,
  #       'iterations': 5,
  #       'delay': 0
  #     }
  # },
};
