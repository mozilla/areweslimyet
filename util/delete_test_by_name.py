#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2012 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

# Remove a test by name and all associated datapoints from a sqlite db

import sys
import os
import sqlite3

if len(sys.argv) != 3:
  sys.stderr.write("Usage: %s <database> <testname>\n" % (sys.argv[0],));
  sys.exit(1);

if not os.path.exists(sys.argv[1]):
  sys.stderr.write("Database '%s' does not exist" % (sys.argv[1],))
  sys.exit(1)

sql = sqlite3.connect(sys.argv[1], timeout=300)
sql.row_factory = sqlite3.Row
cur = sql.cursor()

cur.execute('''SELECT * FROM `benchtester_tests` WHERE `name` = ?''', [ sys.argv[2] ])

totalrows = 0
for test in cur.fetchall():
  testid = int(test['id'])
  cur.execute('DELETE FROM `benchtester_data` WHERE `test_id` = ?', [ testid ])
  deleted = cur.rowcount
  totalrows += deleted + 1
  cur.execute('DELETE FROM `benchtester_tests` WHERE `id` = ?', [ testid ])
  sql.commit()
  print("Deleted test %u with %u datapoints" % ( testid, deleted ))

print("Deleted %u total rows" % totalrows)
