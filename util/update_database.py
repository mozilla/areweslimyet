#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2012 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.


# Converts a database using the older format to the newer format.

import sys
import os
import sqlite3
import time

sys.path.append(os.path.join('.', 'benchtester'))

# We need gTableSchemas to create the new database
try:
  import BenchTester
except:
  sys.stderr.write("Couldn't find benchtester in current directory. Run me from the root!\n");
  sys.exit(1);

if len(sys.argv) < 2:
  sys.stderr.write("Usage: %s <database>\n" % (sys.argv[0],));
  sys.stderr.write("  will create a new database named <database>.new in the\n");
  sys.stderr.write("  newer format. The optional second parameter is one or\n");
  sys.stderr.write("  more tests (by name) to omit from the new database.\n");
  sys.exit(1);

if not os.path.exists(sys.argv[1]):
  sys.stderr.write("Database '%s' does not exist" % (sys.argv[1],))
  sys.exit(1)

omit_tests = sys.argv[2:]
print("Omitting %u tests:" % len(omit_tests))
for x in omit_tests:
  print(" - \"%s\"" % (x,))

newdb = sys.argv[1] + '.new'
print("Creating %s..." % (newdb,))
sql = sqlite3.connect(newdb, timeout=300)
sql.row_factory = sqlite3.Row
cur = sql.cursor()
for schema in BenchTester.gTableSchemas:
  print(schema)
  cur.execute(schema)

# This will speed things up significantly at the expense of ~1GiB memory usage
cur.execute('''PRAGMA cache_size = -1000000''')
cur.execute('''PRAGMA temp_store = 2''')
# The new database is empty if we don't reach COMMIT, so we don't particularly
# care if we corrupt it. This also significantly speeds up the operation.
cur.execute('''PRAGMA journal_mode = OFF''')
cur.execute('''PRAGMA synchronous = OFF''')

# Open old db
print("Opening %s..." % (sys.argv[1],))
cur.execute('''ATTACH DATABASE ? AS old''', [ sys.argv[1] ])

print("Counting rows...")
cur.execute('SELECT COUNT(*) FROM old.benchtester_tests')
totalrows = cur.fetchone()[0]
print("%u total tests" % totalrows)

# Copy all non-excluded tests
# (this was added so I could drop the obsolete Slimtest-TalosTP5 test from old DBs)

updatedrows = 0
starttime = time.time()

cur.execute('SELECT * FROM old.benchtester_builds')
for build in cur.fetchall():
  cur.execute('INSERT INTO benchtester_builds(name, time) VALUES (?, ?)',
              [ build['name'], build['time'] ])
  cur.execute('SELECT last_insert_rowid()')
  newbuildid = cur.fetchone()[0]

  cur.execute('SELECT * FROM old.benchtester_tests WHERE build_id = ?', [ build['id'] ])
  for test in cur.fetchall():
    updatedrows += 1
    if test['name'] in omit_tests:
      continue
    cur.execute('INSERT INTO benchtester_tests(name, time, build_id, successful) '
                'VALUES (?, ?, ?, ?)',
                [ test['name'], test['time'], newbuildid, test['successful'] ])
    cur.execute('SELECT last_insert_rowid()')
    newtestid = cur.fetchone()[0]

    # Pain-full
    # Make sure all datapoints exist
    cur.execute('INSERT OR IGNORE INTO benchtester_datapoints(name) '
                'SELECT datapoint FROM old.benchtester_data WHERE test_id = ?',
                [ test['id'] ])
    # Copy data
    cur.execute('INSERT INTO benchtester_data(test_id, datapoint_id, value) '
                'SELECT ?, p.id, dat.value '
                'FROM old.benchtester_data dat, benchtester_datapoints p '
                'WHERE p.name = dat.datapoint AND dat.test_id = ?',
                [ newtestid, test['id'] ])
    print("[%.02fs] %u/%u" % ((time.time() - starttime), updatedrows, totalrows))

print("Updated %u rows, finishing commit (this could take a while)" % updatedrows)
sql.commit()
print("Done in %ds" % (time.time() - starttime,))
