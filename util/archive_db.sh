#!/bin/bash

# Dumb script to archive a database
# - Drop indexes
# - sqlite VACUUM
# - xz compress

# The test hook (slimtest-batchtester-hook.py) checks for db.xz and, if present,
# refuses to add new tests for that range.

# Copyright © 2012 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

# ./queue_tinderbox_builds.py <batchdir> <json status file>
# Queues all tinderbox builds on FTP not in the list in <json status file>.
# Updates that file with list of builds considered. Used by cronjob to
# auto-queue new tinderbox builds.

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

echo "Running remove duplicate tests"
python "$(dirname "$0")"/remove_duplicate_tests.py "$db"

for table in $(sqlite3 "$db" .tables); do
  for index in $(sqlite3 "$db" ".indices $table"); do
    echo "Dropping index $table -> $index"
    sqlite3 "$db" "DROP INDEX '$index'" || true
  done
done

echo "Vacuuming"
sqlite3 "$db" VACUUM

echo "Compressing"
xz -v9ec "$db" > "$db.xz.temp"
mv -v "$db.xz.temp" "$db.xz"

echo "Done"
