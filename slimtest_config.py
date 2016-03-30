#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2014 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

# Tests for areweslimyet.com. Used by run_slimtest.py or slimtest_batchtester_hook.py

AreWeSlimYetTests = {
  ## A very quick test-run, for testing purposes - doesn't give very useful data
  ## "Slimtest-TalosTP5-Quick":
  # {
  #   'type': "MarionetteTest",
  #   'vars':
  #     {
  #       'test': [ 'benchtester', 'test_memory_usage.py' ],
  #       'entities': 5,
  #       'iterations': 1,
  #       'perTabPause': 1,
  #       'settleWaitTime': 3,
  #       'maxTabs': 3,
  #       'debug': True,
  #       'e10s': True
  #     }
  # },
  ## The current test used for areweslimyet.com. Takes about 90 minutes.
  "Slimtest-TalosTP5-Slow":
  {
    'type': "MarionetteTest",
    'vars':
      {
        'test': [ 'benchtester', 'test_memory_usage.py' ],
        'proxyPort': 3128,
        'e10s': False,
      }
  },
};
