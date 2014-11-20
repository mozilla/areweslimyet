#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2012 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import BenchTester
import os
import sys
import shutil
import tempfile
import re

class EnduranceTest(BenchTester.BenchTest):
  def __init__(self, parent):
    BenchTester.BenchTest.__init__(self, parent)
    parent.add_argument('--jsbridge_port', help="Port to use for jsbridge, so concurrent tests don't collide", default="24242")
    self.name = "EnduranceTest"
    self.parent = parent

  def setup(self):
    self.info("Setting up Endurance module")
    self.ready = True
    self.endurance_results = None

    if 'jsbridge_port' in self.parent.args:
      self.jsport = int(self.parent.args['jsbridge_port'])
    else:
      self.jsport = 24242
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
    import mozrunner
    import jsbridge

    profdir = tempfile.mkdtemp("slimtest_profile")
    self.info("Using temporary profile %s" % profdir)
    #
    # Setup mozmill
    #
    self.info("Mozmill - setting up. Using jsbridge port %u" % (self.jsport,))
    mozmillinst = mozmill.MozMill(jsbridge_port=self.jsport)
    mozmillinst.persisted['endurance'] = testvars
    mozmillinst.add_listener(self.endurance_event, eventType='mozmill.enduranceResults')
    # enduranceCheckpoint is used in slimtest's endurance version
    # to avoid keeping everything in the runtime (it records a lot of numbers,
    # which in turn inflate memory usage, which it's trying to measure)
    mozmillinst.add_listener(self.endurance_checkpoint, eventType='mozmill.enduranceCheckpoint')

    profile = mozrunner.FirefoxProfile(binary=self.tester.binary,
                                       profile=profdir,
                                       addons=[jsbridge.extension_path, mozmill.extension_path],
                                       # Don't open the first-run dialog, it loads a video
                                       # and other things that can screw with benchmarks
                                       preferences={'startup.homepage_welcome_url' : '',
                                                    'startup.homepage_override_url' :'',
                                                    'browser.tabs.remote.autostart': False,
                                                    'browser.displayedE10SPrompt': 5,
                                                    'browser.tabs.remote.autostart.1': False,
                                                    'browser.displayedE10SPrompt.1': 5,
                                                    'browser.tabs.remote.autostart.2': False,
                                                    'browser.displayedE10SPrompt.2': 5,
                                                    'browser.tabs.remote.autostart.3': False,
                                                    'browser.displayedE10SPrompt.3': 5,
                                                    'browser.tabs.remote.autostart.4': False,
                                                    'browser.displayedE10SPrompt.4': 5,
                                                    'browser.tabs.remote.autostart.5': False,
                                                    'browser.displayedE10SPrompt.5': 5,
                                                    'browser.tabs.remote.autostart.6': False,
                                                    'browser.displayedE10SPrompt.6': 5,
                                                    'browser.tabs.remote.autostart.7': False,
                                                    'browser.displayedE10SPrompt.7': 5,
                                                    'browser.tabs.remote.autostart.8': False,
                                                    'browser.displayedE10SPrompt.8': 5,
                                                    'browser.tabs.remote.autostart.9': False,
                                                    'browser.displayedE10SPrompt.9': 5,
                                                    'browser.tabs.remote.autostart.10': False,
                                                    'browser.displayedE10SPrompt.10': 5 })

    # HACK to work around mozrunner's broken stop/wait methods, which nuke all
    # pids matching 'firefox' >= the child pid. This fixes concurrent tests.
    # Bug735501 - fixed in mozmill 2.0+
    class runnerwrap(mozrunner.FirefoxRunner):
      def stop(self):
        if not self.process_handler:
          return
        self.process_handler.kill()
        self.process_handler.wait(timeout=10)
      def wait(self, timeout=None):
        """Wait for the browser to exit."""
        self.process_handler.wait(timeout=timeout)

    runner = runnerwrap(binary=self.tester.binary, profile=profile)
    runner.cmdargs += ['-jsbridge', str(self.jsport)]

    # Add test
    testpath = os.path.join(*testvars['test'])
    if not os.path.exists(testpath):
      return self.error("Test '%s' specifies a test that doesn't exist: %s" % (testname, testpath))
    mozmillinst.tests = [ testpath ]

    # Run test
    self.endurance_results = None
    self.info("Endurance - starting browser")
    try:
      mozmillinst.start(profile=runner.profile, runner=runner)
      self.info("Endurance - running test")
      mozmillinst.run_tests(mozmillinst.tests)
      successful = len(mozmillinst.fails) == 0
    except Exception, e:
      try:
        mozmillinst.stop(fatal=True)
      except: pass
      shutil.rmtree(profdir)
      return self.error("Endurance test run failed -- %s: %s" % (type(e), e))

    self.info("Endurance - cleaning up")
    try:
      # mozmillinst.stop() just calls stop_runner() -> cleanup(). stop_runner()
      # without hard=True can hang (see XXX comment in mozmill), but passing
      # hard=True can cause errors in cleanup(). However, since we nuke the
      # profile ourselves, cleanup is unnecessary.
      mozmillinst.stop_runner(timeout=10, close_bridge=True, hard=True)
    except Exception, e:
      self.error("Failed to properly cleanup mozmill -- %s: %s" % (type(e), e))
    finally:
      shutil.rmtree(profdir)

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
      fails = [y for x in mozmillinst.fails for y in x['fails']]
      return self.error("%u failures occured during test run: %s" % (len(fails), fails))
    self.info("Test '%s' complete" % testname)
    return True
