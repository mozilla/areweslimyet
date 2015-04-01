#!/bin/bash

# Albus's cronjob for updating the exported data
set -e
cd "$(dirname "$0")"/..

# This is a virtualenv with marionette
source marionette-env/bin/activate

# Update git
git pull && git submodule update

# Queue any new tinderbox builds
util/queue_tinderbox_builds.py html/status/batch last_tinderbox.json mozilla-inbound

# Compress logs from >7days ago
(
  cd logs
  while read -d '' -r oldlogfile; do
    if [ ! -z "$oldlogfile" ]; then
        echo ":: Compressing old log $oldlogfile"
	xz -v9ec "$oldlogfile" > "$oldlogfile".xz."$(date +"%Y%m%d%H%M%S")"
        rm "$oldlogfile"
    fi
  done < <(find . -type f -iname '*.log' -mtime +7 -print0)
)

# Import any new mobile data
flock -n ~/mobile.lck tester_scripts/import.sh

# Update all json exports
for x in db/areweslimyet-*.sqlite db/custom-*.sqlite; do
  if [ -f "$x".xz ]; then
      echo ":: Skipping $x due to presence of .xz"
      continue
  fi
  s="$(basename "${x%.sqlite}")"
  s="${s#custom-}"
  if [ -e "$x" ]; then
    ./create_graph_json.py "$x" "$s" html/data
  fi
done

for x in db/custom-*.sqlite; do
  s="$(basename "${x%.sqlite}")"
  s="${s#custom-}"
  if [ -e "$x" ]; then
    ./merge_graph_json.py "${s%-x}" html/data
  fi
done

./merge_graph_json.py areweslimyet html/data

# Sync with mirror
# To turn off data sync add: --exclude=data
if [ -e "./slimuploader_rsa_key" ]; then
  rsync --timeout=60 -ve "ssh -i ./slimuploader_rsa_key" -a --delete-after --delay-updates html/ slimyet@nemu.pointysoftware.net:/www/areweslimyet.com/html/
else
  echo ":: missing key file, not rsyncing"
fi
