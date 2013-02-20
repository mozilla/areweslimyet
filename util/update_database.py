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
sql = sqlite3.connect(newdb, timeout=900)
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

#
# Determine format of old DB
#

# Added benchtester_datapoints table
has_datapoints = 1
try:
  cur.execute('SELECT * FROM old.benchtester_datapoints LIMIT 1')
except sqlite3.OperationalError:
  has_datapoints = 0

# Added meta column to benchtester_data and stopped storing iteration # /
# checkpoint name in the datapoint string
has_meta = 1
try:
  cur.execute('SELECT meta FROM old.benchtester_data LIMIT 1')
except sqlite3.OperationalError:
  has_meta = 0

if has_datapoints and has_meta:
  print("Database is already the newest format!")
  sys.exit(1)

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

    # This should probably be done outside the loop for all tests at once, but
    # then we couldn't support the excluded-tests param. (or we'd have to do a
    # delete-and-vacuum afterwords)
    if not has_datapoints:
      datapoints = cur.execute('SELECT datapoint FROM old.benchtester_data '
                               'WHERE test_id = ?', [ test['id'] ])
    else:
      datapoints = cur.execute('SELECT p.name AS datapoint '
                               'FROM old.benchtester_data d '
                               'JOIN old.benchtester_datapoints p '
                               'ON d.datapoint_id = p.id '
                               'WHERE d.test_id = ?', [ test['id'] ])

    # Given an old datapoint name, returns [ newname, meta ]
    def splitmeta(dp):
      s = dp.split('/', 2)
      iteration = s[0].split(':')
      if len(iteration) > 1:
        dp = '%s:%s' % (iteration[0], s[2])
        iteration = iteration[1]
      else:
        dp = s[2]
        iteration = iteration[0]
      meta = "%s:%u" % (s[1], int(iteration.replace('Iteration ', '')))
      return [ dp, meta ]

    # Insert all datapoint names
    cur.executemany('INSERT OR IGNORE INTO benchtester_datapoints(name) '
                    'VALUES (?)',
                    ( [ splitmeta(row['datapoint'])[0] ]
                      for row in datapoints.fetchall() ))

    # Hey look its the same query again
    if not has_datapoints:
      data = cur.execute('SELECT datapoint, value FROM old.benchtester_data '
                         'WHERE test_id = ?', [ test['id'] ])
    else:
      data = cur.execute('SELECT p.name AS datapoint, d.value '
                         'FROM old.benchtester_data d '
                         'JOIN old.benchtester_datapoints p '
                         'ON d.datapoint_id = p.id '
                         'WHERE d.test_id = ?', [ test['id'] ])

    def rowify(newid, row):
      split = splitmeta(row['datapoint'])
      return [ newid,
               row['value'],
               split[1],
               split[0] ]
    # Insert data
    cur.executemany('INSERT INTO benchtester_data(test_id,datapoint_id,value,meta) '
                    'SELECT ?, p.id, ?, ? '
                    'FROM benchtester_datapoints p '
                    'WHERE p.name = ?',
                    (rowify(newtestid, row) for row in data.fetchall() ))
    sql.commit()
    print("[%.02fs] %u/%u" % ((time.time() - starttime), updatedrows, totalrows))

print("Updated %u rows, in %ds" % (updatedrows, time.time() - starttime))
