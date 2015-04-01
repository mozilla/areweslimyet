#!/bin/bash

set -e

cd "$(dirname "$0")"/..

# This is a virtualenv with marionette
source marionette-env/bin/activate

echo ":: Activated mozmill-1.5-env"

run() {
  echo >&2 ":: Launching try watcher"
  python util/try_watcher.py awsy.cfg html/status/batch
}

while run; do
  echo >&2 ":: try watcher exited, restarting"
  sleep 1
done

echo >&2 "!! try watcher failed or interrupted. Finishing."
