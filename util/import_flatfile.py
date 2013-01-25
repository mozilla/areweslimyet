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
meta = [ 'buildname', 'buildtime', 'testname', 'testtime' ]
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
    if k not in metadata:
        err("Required metadata %s missing :(" % (k,))
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

# FIXME, do we need to fetch push timestamps here?
cur.execute("INSERT OR IGNORE INTO `benchtester_builds` (`name`, `time`) VALUES (?, ?)",
            [ metadata['buildname'], metadata['buildtime'] ])
ret = cur.execute("SELECT `id` FROM `benchtester_builds` WHERE `name` = ?", [ metadata['buildname'] ])
metadata['buildid'] = ret.fetchone()[0]
print("Inserted build %s / %s -> %u" %
      (metadata['buildname'], metadata['buildtime'], metadata['buildid']))


cur.execute("INSERT INTO `benchtester_tests` (`name`, `time`, `build_id`, `successful`) "
            "VALUES (?, ?, ?, 1)",
            [ metadata['testname'], metadata['testtime'], metadata['buildid'] ])
ret = cur.execute("SELECT last_insert_rowid()")
metadata['testid'] = ret.fetchone()[0]
print("Inserted test %u, %s : %s" %
      (metadata['testid'], metadata['testname'], metadata['testtime']))

start = time.time()
cur.executemany("INSERT OR IGNORE INTO `benchtester_datapoints`(name) VALUES (?)",
                ( [datapoint] for datapoint in data.keys() ))

sql.commit()
print("Inserted %u datapoint names in %.02fs" % (cur.rowcount, time.time() - start))

start = time.time()

cur.executemany("INSERT INTO `benchtester_data` "
                "SELECT ?, p.id, ? FROM `benchtester_datapoints` p "
                "WHERE p.name = ?",
                ( [ metadata['testid'], val, datapoint ]
                  for datapoint, val in data.iteritems() ))

sql.commit()
print("Inserted %u datapoints in %.02fs" % (cur.rowcount, time.time() - start))
