#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2012 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import BenchTester
import os
import shutil

import mozprofile
from marionette.runtests import MarionetteTestRunner
from mozlog.structured import commandline


class MarionetteTest(BenchTester.BenchTest):

    def __init__(self, parent):
        BenchTester.BenchTest.__init__(self, parent)
        # NB: If bug 1027022 ever lands we can remove this.
        parent.add_argument('--marionette_port',
                            help="Port to use for marionette, so concurrent tests don't collide",
                            default="24242")
        parent.add_argument('--gecko_log',
                            help="Logfile for gecko output. Defaults to 'gecko.log'",
                            default=None)
        parent.add_argument('--process_count',
                            help="Number of e10s processes to use",
                            default=1)
        self.name = "MarionetteTest"
        self.parent = parent

    def setup(self):
        self.info("Setting up MarionetteTest module")
        self.ready = True
        self.endurance_results = None
        self.port = int(self.parent.args['marionette_port'])
        self.gecko_log = self.parent.args['gecko_log']
        self.process_count = int(self.parent.args['process_count'])
        self.info("Process Count: %d " % self.process_count)

        return True

    def run_test(self, testname, testvars={}):
        if not self.ready:
            return self.error("run_test() called before setup")

        self.info("Beginning marionette test '%s'" % testname)

        e10s = testvars.get("e10s", False)

        prefs = {
            # disable network access
            "network.proxy.socks": "localhost",
            "network.proxy.socks_port": testvars.get("proxyPort", 90000),
            "network.proxy.socks_remote_dns": True,
            "network.proxy.type": 1,  # Socks

            # Don't open the first-run dialog, it loads a video
            'startup.homepage_welcome_url': '',
            'startup.homepage_override_url': '',
            'browser.newtab.url': 'about:blank',

            # make sure e10s is enabled
            "browser.tabs.remote.autostart": e10s,
            "browser.tabs.remote.autostart.1": e10s,
            "browser.tabs.remote.autostart.2": e10s,
            "browser.tabs.remote.autostart.3": e10s,
            "browser.tabs.remote.autostart.4": e10s,
            "browser.tabs.remote.autostart.5": e10s,
            "browser.tabs.remote.autostart.6": e10s,
            "dom.ipc.processCount": self.process_count,

            # prevent "You're using e10s!" dialog from showing up
            "browser.displayedE10SNotice": 1000,

            # We're not testing flash memory usage. Also: it likes to crash in
            # VNC sessions.
            "plugin.disable": True,

            # Specify a communications port
            "marionette.defaultPrefs.port": self.port,

            # override image expiration in hopes of getting less volatile
            # numbers
            "image.mem.surfacecache.min_expiration_ms": 10000
        }

        # Setup a test runner with our prefs and our logger.
        # TODO(ER): We might want to use a larger set of "automation" preferences
        #           until marionette sets them for us. See bug 1123683.
        profile = mozprofile.FirefoxProfile(preferences=prefs)

        runner = MarionetteTestRunner(
            binary=self.tester.binary,
            profile=profile,
            logger=self.parent.logger,
            address="localhost:%d" % self.port,
            gecko_log=self.gecko_log,
            startup_timeout=60)

        # Add test
        testpath = os.path.join(*testvars['test'])
        if not os.path.exists(testpath):
            return self.error("Test '%s' specifies a test that doesn't exist: %s" %
                              (testname, testpath))

        # Add our testvars
        runner.testvars.update(testvars)

        # Run test
        self.info("Marionette - starting browser")
        try:
            self.info("Marionette - running test")
            runner.run_tests([testpath])
            failures = runner.failed
        except Exception, e:
            try:
                runner.cleanup()
            except:
                pass
            return self.error("Marionette test run failed -- %s: %s" % (type(e), e))
        finally:
            # cleanup the profile dir if not already cleaned up
            if os.path.exists(profile.profile):
                shutil.rmtree(profile.profile)

        self.info("Marionette - cleaning up")
        try:
            runner.cleanup()
        except Exception, e:
            self.error(
                "Failed to properly cleanup marionette -- %s: %s" % (type(e), e))
        finally:
            # cleanup the profile dir if not already cleaned up
            if os.path.exists(profile.profile):
                shutil.rmtree(profile.profile)

        self.info("Marionette - saving results")

        self.endurance_results = runner.testvars.get("results", [])

        if not self.tester.add_test_results(testname, self.endurance_results, not failures):
            return self.error("Failed to save test results")
        if failures:
            return self.error("%u failures occured during test run" % failures)
        self.info("Test '%s' complete" % testname)
        return True
