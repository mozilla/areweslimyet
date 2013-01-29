#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2012 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

# Runs all build timestamps in a database through pushlog_lookup, updating them
# to match their pushlog timestamp. Useful if you, say, happened to have thirty
# months of data with bad timestamps :(

import sqlite3
import os
import sys

# Run from root
sys.path.append(os.path.abspath('benchtester'))
import BuildGetter

if len(sys.argv) != 3:
    sys.stderr.write("Requires arguments: sqlitedb branchname")
    sys.exit(1)

gSqlite = sys.argv[1]
gBranch = sys.argv[2] # e.g. integration/mozilla-inbound

sql = sqlite3.connect(gSqlite, timeout=900)
cur = sql.cursor()

cur.execute("SELECT `id`, `name`, `time` FROM benchtester_builds")
builds = 0
touched = 0
for build in cur.fetchall():
    builds += 1
    newstamp = BuildGetter.pushlog_lookup(build[1])
    if not newstamp:
        print("!! Couldn't lookup build %s" % (build[1],))
    if int(newstamp) != int(build[2]):
        touched += 1
        print("Updating build %s from %u to %u" % (build[1], build[2], newstamp))
        cur.execute("UPDATE `benchtester_builds` SET `time` = ? WHERE `id` = ?",
                    [newstamp, build[0]])

sql.commit()

print("Looked at %u builds and updated %u" % (builds, touched))
