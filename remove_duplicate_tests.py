#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2012 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.


# Remove all but the most recent successful test (or most recent if all failed)
# for each test type for each build. Used trim DBs before they're archived.
# - Remove indexes
# - Remove duplicate tests
# - VACUUM

import sys
import os
import sqlite3

if len(sys.argv) != 2:
  sys.stderr.write("Usage: %s <database>\n" % (sys.argv[0],));
  sys.exit(1);

if not os.path.exists(sys.argv[1]):
  sys.stderr.write("Database '%s' does not exist" % (sys.argv[1],))
  sys.exit(1)

sql = sqlite3.connect(sys.argv[1])
sql.row_factory = sqlite3.Row
cur = sql.cursor()

testnames = set(map(lambda x: x['name'], sql.execute('''SELECT DISTINCT `name` FROM `benchtester_tests`''').fetchall()))
print("%u test names: %s" % (len(testnames), testnames))

qbuilds = sql.execute('''SELECT `id`, `name` FROM `benchtester_builds`''')

totalrows = 0
totaldatapoints = 0
for build in qbuilds:
  for test in testnames:
    newest = sql.execute('''SELECT `id`, `build_id`, `name` FROM `benchtester_tests`
                            WHERE `build_id` = ? AND `name` = ?
                            ORDER BY `successful` DESC, `time` DESC
                            LIMIT 1''', [build['id'], test]).fetchone()
    if newest:
      oldtests = cur.execute('''SELECT `id` FROM `benchtester_tests` WHERE `build_id` = ? AND `name` = ? AND NOT `id` = ?''', [build['id'], test, newest['id']])
      i = 0
      x = 0
      for deleteme in oldtests.fetchall():
        i += 1
        cur.execute('''DELETE FROM `benchtester_data` WHERE `test_id` = ?''', [deleteme['id']])
        x += cur.rowcount
        cur.execute('''DELETE FROM `benchtester_tests` WHERE `id` = ?''', [deleteme['id']])
      if i:
        print("Deleted %u rows with %u datapoints for %s/%s" % (i, x, build['name'], test))
        totalrows += i
        totaldatapoints += x

sql.commit()
print("Deleted total of %u rows with %u datapoints. A vacuum will be required to actually reclaim this space" % (totalrows, totaldatapoints))
