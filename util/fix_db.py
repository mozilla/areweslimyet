#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2012 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.

# Between Feb 14th and Feb 20th util/update_db.py would mangle the metadata for
# datapoints with units. This looks for said datapoints and fixes them.

# Leaves a good bit of trash behind, consider running util/trim_db.sh and
# |sqlite3 db VACUUM| when finished

import sys
import os
import sqlite3
import time



if len(sys.argv) < 2:
  sys.stderr.write("Usage: %s <database>\n" % (sys.argv[0],));
  sys.exit(1);

if not os.path.exists(sys.argv[1]):
  sys.stderr.write("Database '%s' does not exist" % (sys.argv[1],))
  sys.exit(1)

sql = sqlite3.connect(sys.argv[1])
sql.row_factory = sqlite3.Row
cur = sql.cursor()

# This will speed things up significantly at the expense of ~1GiB memory usage
cur.execute('''PRAGMA cache_size = -1000000''')
cur.execute('''PRAGMA temp_store = 2''')

print("Selecting corrupt data...")
baddata = cur.execute("SELECT * FROM benchtester_data "
                      "WHERE meta LIKE '%:cnt:%' OR meta LIKE '%:pct:%'")

baddata = baddata.fetchall()

total = len(baddata)

i = 0
for row in baddata:
  i += 1
  print("Fixing [%u/%u]" % (i, total))
  badmeta = row['meta'].split(':')
  if len(badmeta) is not 3:
    die("Bad meta: %s" % (badmeta,))

  goodmeta = "%s:%s" % (badmeta[0], badmeta[2])

  # fix DP name
  cur.execute("INSERT OR IGNORE INTO benchtester_datapoints(name) "
              "SELECT ? || name FROM benchtester_datapoints "
              "WHERE id = ?",
              [ badmeta[1] + ':', row['datapoint_id'] ])

  # fix data
  cur.execute("INSERT INTO benchtester_data(test_id,datapoint_id,value,meta) "
              "VALUES (?, ?, ?, ?)",
              [ row['test_id'], row['datapoint_id'], row['value'], goodmeta ])


print("Dropping bad")
cur.execute("DELETE FROM benchtester_data "
            "WHERE meta LIKE '%:cnt:%' OR meta LIKE '%:pct:%'")

print("Commit...")
sql.commit()
print("DONE")
