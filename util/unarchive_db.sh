#!/bin/bash

# Dumb script to unarchive a database
# - Decompress
# - re-add sqlite indexes

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

dbxz="$1"
db="${dbxz%.xz}"
if [ -z "$dbxz" ] || [ ! -f "$dbxz" ]; then
  echo >&2 "Need the name of an existing database"
  exit 1
fi
if [ -f "$fb" ]; then
  echo >&2 "$db exists, refusing to overwrite"
  exit 1
fi

echo "Decompressing"
xz -vdc "$dbxz" > "$db"
# Zero XZ file to free space, but don't delete it yet
# (tester uses presence of .xz to mean 'dont touch this DB')
> "$dbxz"

echo "Re-adding indexes"
echo ":: Adding test_lookup"
sqlite3 "$db" 'CREATE INDEX IF NOT EXISTS test_lookup ON benchtester_tests ( name, build_id DESC )'
echo ":: Adding data_for_test"
sqlite3 "$db" 'CREATE INDEX IF NOT EXISTS data_for_test ON benchtester_data ( test_id DESC, datapoint_id )'

# Now we can get rid of dummy .xz
rm -v "$dbxz"
echo "Done"
