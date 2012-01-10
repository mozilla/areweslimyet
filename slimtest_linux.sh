#!/bin/bash

set -e
cd "$(dirname "$0")"
startdir="$PWD"
commit="$1"

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

echo ":: Running test"
export PYTHON=python2
python2 ./run_slimtest.py --logfile "logs/$(date +%Y%m%d_%H%M%S.log)" \
                          --autobuild-commit "$commit" \
                          --autobuild-repo ../mozilla-central \
                          --autobuild-objdir ../ff-dbg \
                          --autobuild-mozconfig ../m-ff-dbg.mzc \
                          --autobuild-pull \
                          --sqlitedb slimtest.sqlite
