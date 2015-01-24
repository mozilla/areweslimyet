#!/bin/bash

set -e

cd "$(dirname "$0")"/..

# This is a virtualenv with the marionette client
source marionette-env/bin/activate

echo ":: Activated marionette-env"

clean() {
  echo >&2 ":: Cleaning house"
  # Misc leftovers from interrupting the tester
  rm -rf /tmp/*BuildGetter* /tmp/*slimtest_profile*
  killall gconfd-2 dbus-launch firefox Xvnc dbus-daemon || true
}
run() {
  echo >&2 ":: Launching tester"
  python benchtester/BatchTester.py -p 8 --batch html/status/batch \
    --hook slimtest_batchtester_hook.py -l logs --repo mozilla-inbound \
    --mozconfig slimtest.mozconfig --objdir slimtest-objdir \
    --status-file html/status/status.json \
    --status-resume --skip-existing
}

trap "clean" EXIT SIGINT SIGTERM
while clean && run; do
  echo >&2 ":: Tester exited, restarting"
  sleep 1
done

echo >&2 "!! Tester failed or interrupted. Finishing."
