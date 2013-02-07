#!/bin/bash

# Copyright © 2012 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

# Dumb script to archive a database
# - Drop indexes
# - sqlite VACUUM
# - xz compress

# The test hook (slimtest-batchtester-hook.py) checks for db.xz and, if present,
# refuses to add new tests for that range.

set -e

db="$1"
if [ -z "$db" ] || [ ! -f "$db" ]; then
  echo >&2 "Need the name of an existing database"
  exit 1
fi
if [ -f "$db.xz" ]; then
  echo >&2 "$db.xz exists, refusing to overwrite"
  exit 1
fi

# Create dummy db.xz file so tester knows the database is now considered
# archived
touch "$db.xz"
# Wait for any current tests using the db to go away
while users="$(lsof "$db")" && [ ! -z "$users" ]; do
  echo ":: DB in use, waiting"
  echo "$users"
  sleep 1
done

before="$(du -h $db)"

echo ":: Current DB size is $before"

echo ":: Removing incomplete tests"
time sqlite3 "$db" 'DELETE FROM benchtester_tests WHERE successful = 0; SELECT total_changes()'

echo ":: Removing orphaned data"
time sqlite3 "$db" 'DELETE FROM benchtester_data WHERE test_id IN
                    (
                     SELECT DISTINCT d.test_id FROM benchtester_data d
                     LEFT JOIN benchtester_tests t ON t.id = d.test_id
                     WHERE t.id IS NULL
                    ); SELECT total_changes()'

echo ":: Removing unreferenced datapoints"
time sqlite3 "$db" 'DELETE FROM benchtester_datapoints WHERE id IN (
                      SELECT DISTINCT id FROM benchtester_datapoints p
                      LEFT JOIN benchtester_data d ON d.datapoint_id = p.id
                      WHERE d.datapoint_id IS NULL
                    ); SELECT total_changes()'

echo ":: Removing unused builds"
time sqlite3 "$db" 'DELETE FROM benchtester_builds WHERE id IN (
                      SELECT DISTINCT b.id FROM benchtester_builds b
                      LEFT JOIN benchtester_tests t ON t.build_id = b.id
                      WHERE t.build_id IS NULL
                    ); SELECT total_changes()'

for table in $(sqlite3 "$db" .tables); do
  for index in $(sqlite3 "$db" ".indices $table"); do
    echo ":: Dropping index $table -> $index"
    sqlite3 "$db" "DROP INDEX '$index'" || true
  done
done

echo ":: Vacuuming"
time sqlite3 "$db" VACUUM

echo "Compressing"
time xz -v9ec "$db" > "$db.xz.temp"
mv -v "$db.xz.temp" "$db.xz"
rm -v "$db"

echo "Done"
echo "Before: $before"
echo "After: $(du -h "$db.xz")"
