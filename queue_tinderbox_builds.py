#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2012 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

# ./queue_tinderbox_builds.py <batchdir> <json status file>
# Queues all tinderbox builds on FTP not in the list in <json status file>.
# Updates that file with list of builds considered. Used by cronjob to
# auto-queue new tinderbox builds.

import sys
import json
import os

def stat(msg):
  sys.stderr.write("%s\n" % (msg,))

def err(msg):
  stat(msg)
  sys.exit(1)

if len(sys.argv) != 3 or not os.path.exists(sys.argv[2]):
  err("Incorrect usage. See comments")

batchdir = sys.argv[1]
knownbuilds = sys.argv[2]

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), "benchtester")))
import BuildGetter
BuildGetter.output = sys.stderr

knownfp = file(knownbuilds, 'r')
old_builds = json.load(knownfp)
knownfp.close()

builds = BuildGetter.list_tinderbox_builds()
if not len(builds):
  stat("No builds to queue")
  sys.exit(0)

stat("Comparing %u builds on tinderbox with %u known builds" % (len(builds), len(old_builds)))

def queue_build(timestamp):
  out = { 'mode' : 'tinderbox', 'prioritize' : True, 'firstbuild' : str(timestamp) }
  batchfile = os.path.join(batchdir, "tinderbox-%u.autoqueue" % (timestamp,))
  if os.path.exists(batchfile):
    err("Failed: file \"%s\" already exists" % (batchfile,))

  f = open(batchfile, 'w')
  json.dump(out, f)
  f.close()

  stat("Queuing build %s" % (out,))

i = 0
for x in builds:
  if x not in old_builds:
    i += 1
    queue_build(x)

knownfp = file(knownbuilds, 'w')
json.dump(builds, knownfp)
knownfp.close()

stat("Queued %u builds" % (i,))
