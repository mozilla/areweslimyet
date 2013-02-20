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

echo ":: Trimming db..."
"$(dirname "$0")"/repack_db.sh "$db"

for index in $(sqlite3 "$db" ".indices"); do
  echo ":: Dropping index $index"
  sqlite3 "$db" "DROP INDEX '$index'"
done

echo ":: Vacuuming"
time sqlite3 "$db" VACUUM

vacuum="$(du -h $db)"

echo ":: After vacuum: $vacuum"

echo ":: Compressing"
time xz -v9ef "$db"

echo "Done"
echo "Before:     $before"
echo "Vacuumed:   $vacuum"
echo "Compressed: $(du -h "$db.xz")"
