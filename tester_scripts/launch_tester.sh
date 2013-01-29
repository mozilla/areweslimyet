#!/bin/bash

set -e
cd "$(dirname "$0")"

# Setup a dbus-session, as without one firefox seems
# to auto-spawn them, then never clean them up
#eval 'dbus-launch --sh-syntax'
#trap "kill $DBUS_SESSION_BUS_PID" EXIT
#export DBUS_SESSION_BUS_ADDRESS
#export DBUS_SESSION_BUS_PID
#/usr/lib/libgconf2-4/gconfd-2 --spawn

clean() {
  echo >&2 ":: Cleaning house"
  rm -rf /tmp/*BuildGetter* /tmp/*slimtest_profile*
  killall gconfd-2 dbus-launch firefox Xtightvnc dbus-daemon || true
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
