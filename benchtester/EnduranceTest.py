#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2012 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import BenchTester
import os
import re

class EnduranceTest(BenchTester.BenchTest):
  def __init__(self, parent):
    BenchTester.BenchTest.__init__(self, parent)
    self.name = "EnduranceTest"
    self.parent = parent

  def setup(self):
    self.info("Setting up Endurance module")
    self.ready = True
    self.endurance_results = None

    return True

  def endurance_event(self, obj):
    if obj['iterations']:
      self.info("Got enduranceResults callback")
      self.endurance_results = obj
    else:
      self.error("Got endurance test result with 0 iterations: %s" % obj)

  def endurance_checkpoint(self, obj):
    if obj['checkpoints']:
      self.info("Got enduranceCheckpoint callback")
      if not self.endurance_results:
        self.endurance_results = { 'iterations': [] }
      self.endurance_results['iterations'].append(obj)
    else:
      self.error("Got endurance checkpoint with no data: %s" % obj)

  def run_test(self, testname, testvars={}):
    if not self.ready:
      return self.error("run_test() called before setup")

    self.info("Beginning endurance test '%s'" % testname)

    import mozmill

    # Setup mozmill
    self.info("Mozmill - setting up.")

    preferences = { 'startup.homepage_welcome_url': '',
                    'startup.homepage_override_url': '' }
    # Uncomment to enable jsbridge logging
    #preferences['extensions.jsbridge.log'] = True
    profile_args = dict(preferences=preferences)

    runner_args = dict(binary=self.tester.binary)
    # Uncomment to enable the browser's jsconsole
    #runner_args['cmdargs'] = ['-jsconsole']

    mozmillinst = mozmill.MozMill.create(runner_args=runner_args, profile_args=profile_args)

    mozmillinst.persisted['endurance'] = testvars
    mozmillinst.add_listener(self.endurance_event, eventType='mozmill.enduranceResults')
    # enduranceCheckpoint is used in slimtest's endurance version
    # to avoid keeping everything in the runtime (it records a lot of numbers,
    # which in turn inflate memory usage, which it's trying to measure)
    mozmillinst.add_listener(self.endurance_checkpoint, eventType='mozmill.enduranceCheckpoint')

    # Add test
    testpath = os.path.join(*testvars['test'])
    if not os.path.exists(testpath):
      return self.error("Test '%s' specifies a test that doesn't exist: %s" % (testname, testpath))
    # mozmill-2 requires an absolute path
    testpath = os.path.abspath(testpath)

    # Run test
    self.endurance_results = None
    test_results = None;
    try:
      self.info("Endurance - running test")
      mozmillinst.run(tests=[ { "path": testpath } ])
      test_results = mozmillinst.finish()
      successful = len(test_results.fails) == 0
    except Exception, e:
      try:
        mozmillinst.finish(fatal=True)
      except: pass
      return self.error("Endurance test run failed -- %s: %s" % (type(e), e))

    self.info("Endurance - cleaning up")
    try:
      mozmillinst.finish(fatal=True)
    except Exception, e:
      self.error("Failed to properly cleanup mozmill -- %s: %s" % (type(e), e))

    self.info("Endurance - saving results")

    if not self.endurance_results:
      return self.error("Test did not return any endurance data!")

    results = list()
    for x in range(len(self.endurance_results['iterations'])):
      iteration = self.endurance_results['iterations'][x]
      for checkpoint in iteration['checkpoints']:
        # Endurance adds [i:0, e:5]
        # Because iterations might not be in order when
        # passed from enduranceCheckpoint, parse this.
        label_re = re.match("^(.+) \[i:(\d+) e:\d+\]$", checkpoint['label'])
        if not label_re:
          self.error("Checkpoint '%s' doesn't look like an endurance checkpoint!" % checkpoint['label'])
          next
        iternum = int(label_re.group(2))
        label = label_re.group(1)
        for memtype,memval in checkpoint['memory'].items():
          if type(memval) is dict:
            prefix = memval['unit'] + ":"
            memval = memval['val']
          else:
            prefix = ""
          results.append([ "%s%s" % (prefix, memtype), memval, "%s:%u" % (label, iternum) ])

    if not self.tester.add_test_results(testname, results, successful):
      return self.error("Failed to save test results")
    if not successful:
      fails = [y for x in test_results.fails for y in x['fails']]
      return self.error("%u failures occured during test run: %s" % (len(fails), fails))
    self.info("Test '%s' complete" % testname)
    return True
