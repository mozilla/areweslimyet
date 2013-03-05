#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2012 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

# Import a flat datafile of the format
# key
# value
# key
# ...

# 'buildname' 'buildtime' 'testname' and 'testtime' are special keys, the rest
# are treated as datapoints.

import sqlite3
import os
import sys
import re
import pprint
import time
import datetime

def err(msg):
    sys.stderr.write(msg + '\n')
    sys.exit(1)

if len(sys.argv) != 3:
    err("Usage: %s <dbdir> <file>" % (sys.argv[0],))

dbdir = sys.argv[1]
filename = sys.argv[2]

keyvalues = dict()
infile = open(filename)
meta = [ 'buildname', 'buildtime', 'testname', 'testtime', 'mode' ]

metadata = dict()
data = dict()
for key in infile:
    val = infile.next().strip()
    key = key.strip()
    if key in meta:
        metadata[key] = val
    elif key in data:
        print("!! Existing key, adding")
        data[key] += int(val)
    else:
        data[key] = int(val)

for k in meta:
    if k != "mode" and k not in metadata:
        err("Required metadata %s missing :(" % (k,))
# Mode is 'insert' or 'replace' to add a new test or blow away all other tests
# for said build
if 'mode' not in metadata:
    metadata['mode'] = "insert"

if metadata['mode'] not in [ 'insert', 'replace' ]:
    err("Invalid mode: %s" % (metadata['mode'],))

print("Got %u datavalues, inserting" % len(data))

filedate = datetime.datetime.utcfromtimestamp(int(metadata['buildtime'])).date()
dbname = "areweslimyet-%04u-%02u.sqlite" % (filedate.year, filedate.month)
dbpath = os.path.join(dbdir, dbname)
print("Using database %s" % (dbpath,))

if os.path.exists(dbpath + '.xz'):
    err("Database appears to be archived, cannot import")
if not os.path.exists(dbpath):
    err("Database does not exist yet! Exiting for sanity")

sql = sqlite3.connect(dbpath)

cur = sql.cursor()

#
# Insert build
#
cur.execute("INSERT OR IGNORE INTO `benchtester_builds` (`name`, `time`) VALUES (?, ?)",
            [ metadata['buildname'], metadata['buildtime'] ])
ret = cur.execute("SELECT `id` FROM `benchtester_builds` WHERE `name` = ?", [ metadata['buildname'] ])
metadata['buildid'] = ret.fetchone()[0]
print("Inserted build %s / %s -> %u" %
      (metadata['buildname'], metadata['buildtime'], metadata['buildid']))

#
# Nuke old tests if mode=replace
#
if metadata['mode'] == "replace":
    print("Replace specified, blowing away old tests for this build...")
    cur.execute("DELETE FROM `benchtester_tests` "
                "WHERE `build_id` = ? AND `name` = ?",
                [ metadata['buildid'], metadata['testname'] ])
    print("Deleted %u old tests" % (cur.rowcount))

#
# Insert test
#
cur.execute("INSERT INTO `benchtester_tests` (`name`, `time`, `build_id`, `successful`) "
            "VALUES (?, ?, ?, 1)",
            [ metadata['testname'], metadata['testtime'], metadata['buildid'] ])
ret = cur.execute("SELECT last_insert_rowid()")
metadata['testid'] = ret.fetchone()[0]
print("Inserted test %u, %s : %s" %
      (metadata['testid'], metadata['testname'], metadata['testtime']))

#
# Filter datapoint names into desktop AWSY's datapoint/value/meta format
#

# List of [ dp, val, meta ]
filtered_data = list()

for orgdp in data.keys():
    s = orgdp.split('/', 2)
    iteration = s[0].split(':')
    if len(iteration) > 1:
        dp = '%s:%s' % (iteration[0], s[2])
        iteration = iteration[1]
    else:
        dp = s[2]
        iteration = iteration[0]
    meta = "%s:%u" % (s[1], int(iteration.replace('Iteration ', '')))
    filtered_data.append([ dp, data[orgdp], meta ])

unique_dp_names = set(dp[0] for dp in filtered_data)

#
# Insert datapoint names
#
start = time.time()
cur.executemany("INSERT OR IGNORE INTO `benchtester_datapoints`(name) VALUES (?)",
                ( [datapoint] for datapoint in unique_dp_names ))

sql.commit()
print("Inserted %u datapoint names in %.02fs" % (cur.rowcount, time.time() - start))

#
# Insert data
#
start = time.time()

cur.executemany("INSERT INTO `benchtester_data` "
                "SELECT ?, p.id, ?, ? FROM `benchtester_datapoints` p "
                "WHERE p.name = ?",
                ( [ metadata['testid'], dp[1], dp[2], dp[0] ]
                  for dp in filtered_data ))

sql.commit()
print("Inserted %u datapoints in %.02fs" % (cur.rowcount, time.time() - start))
