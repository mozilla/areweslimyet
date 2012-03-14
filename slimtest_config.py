#!/usr/bin/env python

# Tests for areweslimyet.com. Used by run_slimtest.py or slimtest_batchtester_hook.py

AreWeSlimYetTests = {
  "Slimtest-TalosTP5":
  {
    'type': "EnduranceTest",
    'vars':
      {
        'test': [ 'mozmill_endurance_test' ],
        'entities': 100,
        'iterations': 5,
        'delay': 0
      }
  },
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
};