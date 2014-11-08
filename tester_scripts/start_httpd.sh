#!/bin/bash
set -e

cd "$(dirname "$0")"

# This is a virtualenv with mozmill 1.5
source py2env/bin/activate

killall thttpd nginx || true

# we use a small thttpd compile to handle cgi requests to /status/request.cgi
thttpd -C thttpd/thttpd.cfg

# This is the TP5 pageset listening on ports 8001-8100
nginx -p nginx/ -c conf/nginx.conf

# This is just nginx serving the root of the html/ directory, with
# html/status/request.cgi going to thttpd since nginx can't do native cgi
nginx -p nginx_local/ -c conf/nginx.conf
