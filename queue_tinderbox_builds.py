#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2012 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

# ./queue_tinderbox_builds.py <batchdir> <from>
# Given timestamp <from>, queues all tinderbox builds on FTP *after* that time,
# prints a single timestamp of the newest build queued. Used by cronjob to
# auto-queue new tinderbox builds.

import sys
import json
import os

def stat(msg):
  sys.stderr.write("%s\n" % (msg,))

def err(msg):
  stat(msg)
  sys.exit(1)

if len(sys.argv) != 3 or str(int(sys.argv[2])) != sys.argv[2]:
  err("Incorrect usage. See comments")

batchdir = sys.argv[1]
fromtime = int(sys.argv[2])

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), "benchtester")))
import BuildGetter
BuildGetter.output = sys.stderr

builds = BuildGetter.list_tinderbox_builds(fromtime + 1)
if not len(builds):
  stat("No builds to queue")
  sys.exit(0)

stat("Queueing %u builds: %s" % (len(builds), builds))
out = { 'mode' : 'tinderbox', 'prioritize' : True, 'firstbuild' : builds[0] }
if len(builds) > 1:
  out['lastbuild'] = builds[-1]

batchfile = os.path.join(batchdir, "tinderbox.autoqueue")
if os.path.exists(batchfile):
  err("Failed: file \"%s\" already exists" % (batchfile,))

f = open(batchfile, 'w')
json.dump(out, f)
f.close()

stat("Queued job: %s" % (out,))

# Only thing written to stdout. Lets us do things like
# ./queue_tinderbox_builds.py $(cat last_build.txt) > last_build.txt
print(builds[-1])
