#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2012 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.


# Converts a database using the older unversioned format to the v1 format.

import os
import re
import sqlite3
import sys
import time

sys.path.append(os.path.join('.', 'benchtester'))

# We need gTableSchemas to create the new database
try:
  import BenchTester
except:
  sys.stderr.write("Couldn't find benchtester in current directory. Run me from the root!\n");
  sys.exit(1);


# memory report 'kind' constants
KIND_NONHEAP = 0
KIND_HEAP = 1
KIND_OTHER = 2

# memory report 'units' constants
UNITS_BYTES = 0
UNITS_COUNT = 1
UNITS_COUNT_CUMULATIVE = 2
UNITS_PERCENTAGE = 3

if len(sys.argv) < 2:
  sys.stderr.write("Usage: %s <database>\n" % (sys.argv[0],));
  sys.stderr.write("  will create a new database named <database>.new in the\n");
  sys.stderr.write("  newer format. The optional second parameter is one or\n");
  sys.stderr.write("  more tests (by name) to omit from the new database.\n");
  sys.exit(1);

if not os.path.exists(sys.argv[1]):
  sys.stderr.write("Database '%s' does not exist" % (sys.argv[1],))
  sys.exit(1)

newdb = sys.argv[1] + '.new'
print("Creating %s..." % (newdb,))
sql = sqlite3.connect(newdb, timeout=900)
sql.row_factory = sqlite3.Row
cur = sql.cursor()
for schema in BenchTester.gTableSchemas:
  print(schema)
  cur.execute(schema)

# This will speed things up significantly at the expense of ~4GiB memory usage
cur.execute('''PRAGMA cache_size = -4000000''')
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

db_version = None
try:
  cur.execute('SELECT * FROM old.benchtester_version LIMIT 1')
  db_version = cur.fetchone()['version']
except sqlite3.OperationalError:
  db_version = 0

if db_version == BenchTester.gVersion:
  print("Database is up to date, version = %s" % db_version)
  sys.exit(1)
elif db_version != 0 or BenchTester.gVersion != 1:
  print("This script currently only handles 0 => 1")
  sys.exit(1)
else:
  print("Upgrading db version from %s to %s" % (db_version, BenchTester.gVersion))

starttime = time.time()

# Set the DB version
cur.execute('INSERT INTO benchtester_version(version) VALUES ( ? )', (BenchTester.gVersion, ))

# Add the benchtester_checkpoints
cur.execute('SELECT DISTINCT meta FROM old.benchtester_data')
checkpoints = set([ row['meta'].split(':')[0] for row in cur.fetchall() ])
cur.executemany('INSERT INTO benchtester_checkpoints(name) '
                'VALUES (?)', ( [ checkpoint ] for checkpoint in checkpoints ))

print("[%.02fs] Inserted %d checkpoints" % ((time.time() - starttime), len(checkpoints)))

# Add an entry for Main in benchtester_procs
cur.execute('INSERT INTO benchtester_procs(name) VALUES ( ? )', ('Main', ))

# Add an entry for mozilla-inbound in benchtester_repos
cur.execute('INSERT INTO benchtester_repos(name) VALUES ( ? )', ('mozilla-inbound', ))

# Fill in the datapoints table
cur.execute('SELECT DISTINCT name AS datapoint '
            'FROM old.benchtester_datapoints d ')

# Given an old datapoint name, returns [ newname, units ]
def splitunits(dp):
  units = UNITS_BYTES
  match = re.match(r'(cnt|pct):(.*)', dp)

  if match:
    dp = match.group(2)
    units = UNITS_COUNT if match.group(1) == 'cnt' else UNITS_PERCENTAGE

  return [ dp, units ]

datapoints = set(( splitunits(row['datapoint'])[0] for row in cur.fetchall() ))

print("[%.02fs] Selected %d datapoints" % ((time.time() - starttime), len(datapoints)))

# Insert all datapoint names
cur.executemany('INSERT OR IGNORE INTO benchtester_datapoints(name) '
                'VALUES (?)',
                ( [ dp ] for dp in datapoints ))

print("[%.02fs] Inserted %d datapoints" % ((time.time() - starttime), len(datapoints)))

# Copy the builds table
cur.execute('INSERT INTO benchtester_builds(id, name, time, repo_id) '
            'SELECT id, name, time, 1 from old.benchtester_builds')

print("[%.02fs] Copied benchtester_builds" % (time.time() - starttime))

# Copy the tests table
cur.execute('INSERT INTO benchtester_tests(id, name, time, build_id, successful) '
            'SELECT id, name, time, build_id, successful FROM old.benchtester_tests')

print("[%.02fs] Copied benchtester_tests" % (time.time() - starttime))

# Fill in the new benchtester_data table
data = cur.execute('SELECT d.test_id, p.name AS datapoint, d.value, d.meta '
                   'FROM old.benchtester_data d '
                   'JOIN old.benchtester_datapoints p '
                   'ON d.datapoint_id = p.id ')

def splitmeta(meta):
  return meta.split(':')

def rowify(row):
  dp, units = splitunits(row['datapoint'])
  checkpoint, iteration = splitmeta(row['meta'])
  proc_id = 1 # there's just the Main process in version 0

  # we just say kind is heap if under explicit, other if not
  kind = KIND_HEAP if dp.startswith('explicit') else KIND_OTHER

  return [ row['test_id'],
           proc_id,
           int(iteration),
           row['value'],
           units,
           kind,
           dp,
           checkpoint ]

# Insert data
cur.executemany('INSERT INTO benchtester_data(test_id,datapoint_id,checkpoint_id,proc_id,iteration,value,units,kind) '
                'SELECT ?, p.id, c.id, ?, ?, ?, ?, ? '
                'FROM benchtester_datapoints p, '
                '     benchtester_checkpoints c '
                'WHERE p.name = ? AND c.name = ?',
                ( rowify(row) for row in data.fetchall() ))

print("[%.02fs] Inserted benchtester_data" % (time.time() - starttime))

sql.commit()

print("[%.02fs] Committed everything" % (time.time() - starttime))

