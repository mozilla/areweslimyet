#!/bin/bash

# Copyright © 2014 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

# This is just a run_slimtest.py wrapper:
# - Starts vncserver on :9
# - Starts the nginx instance in ./nginx/
# - Selects python2 binary if necessary
# - Runs ./run_slimtest.py "$@"
# - Cleans up VNC/nginx

set -e
cd "$(dirname "$0")"
startdir="$PWD"

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

# Assumes ./nginx/ has a nginx prefix with TP5 setup
echo ":: Starting nginx"
nginx -p $PWD/nginx/ -c $PWD/nginx/conf/nginx.conf

echo ":: Starting VNC"
vncserver :9
export DISPLAY=:9

echo ":: Running test"
# Use py2 binary on systems that have python -> python 3.x
which python2 &>/dev/null && PYTHON=python2 || PYTHON=python
export PYTHON
$PYTHON ./run_slimtest.py "$@"
