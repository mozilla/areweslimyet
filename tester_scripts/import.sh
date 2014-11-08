#!/bin/bash
set -e
cd "$(dirname "$0")"
if [ -z "$(ls ./mobile)" ]; then
  echo ":: No new builds to import"
  exit
fi

for infile in ./mobile/*; do
    echo ":: Importing $infile"
    basefile="${infile%.gz}"
    [ "$basefile" = "$infile" ] || gzip -dv "$infile"
    python util/import_flatfile.py db/ "$basefile"
    rm -v "$basefile"
done
