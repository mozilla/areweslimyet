#!/bin/bash

# Albus's cronjob for updating the exported data
set -e
cd "$(dirname "$0")"

# Update git
git pull && git submodule update

# Queue any new tinderbox builds
util/queue_tinderbox_builds.py html/status/batch last_tinderbox.json integration/mozilla-inbound

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
flock -n ~/mobile.lck ./import.sh

# Update all json exports
for x in db/areweslimyet-*.sqlite db/custom-*.sqlite; do
  if [ -f "$x".xz ]; then
      echo ":: Skipping $x due to presence of .xz"
      continue
  fi
  s="$(basename "${x%.sqlite}")"
  s="${s#custom-}"
  ./create_graph_json.py "$x" "$s" html/data
done

for x in db/custom-*.sqlite; do
  s="$(basename "${x%.sqlite}")"
  s="${s#custom-}"
  ./merge_graph_json.py "${s%-x}" html/data
done

./merge_graph_json.py areweslimyet html/data

# Sync with mirror
# To turn off data sync add: --exclude=data
# rsync <censored ...>
