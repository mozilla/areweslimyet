#!/bin/bash

# Copyright © 2012 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

set -e
cd "$(dirname "$0")"
startdir="$PWD"

[ ! -z "$timestamp" ] && timestamp="--buildtime $timestamp"
[ -z "$commit" ] && commit="tip"

[ -d "logs" ] || mkdir -v logs


cleanup()
{
  echo ":: Cleaning up env"
  cd "$startdir"
  echo ":: Shutting down vnc"
  vncserver -kill :9 || true
  pid=$(cat nginx/logs/nginx.pid 2>/dev/null || true)
  if [ ! -z "$pid" ]; then
    echo ":: Killing nginx"
    kill $pid || true
    sleep 1
    kill -9 $pid || true
  else
    echo ":: No nginx"
  fi
}
trap cleanup EXIT

cleanup

echo ":: Starting nginx"
./nginx/nginx -p $PWD/nginx/
echo ":: Starting VNC"
vncserver :9
export DISPLAY=:9

echo ":: Nuking objdir"
# We use ccache so the extra time it saves us to keep this
# isn't worth the probability of random build fails
rm -rf ./slimtest-build

echo ":: Running test"
# Use py2 binary on systems that have python -> python 3.x
which python2 &>/dev/null && PYTHON=python2 || PYTHON=python
export PYTHON
$PYTHON ./run_slimtest.py "$@"
