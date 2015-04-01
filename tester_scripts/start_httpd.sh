#!/bin/bash
set -e

cd "$(dirname "$0")"/..

killall thttpd nginx || true

# we use a small thttpd compile to handle cgi requests to /status/request.cgi
thttpd/thttpd -C thttpd/thttpd.cfg

# This is the TP5 pageset listening on ports 8001-8100
/usr/sbin/nginx -p nginx/ -c conf/nginx.conf

# This is just nginx serving the root of the html/ directory, with
# html/status/request.cgi going to thttpd since nginx can't do native cgi
/usr/sbin/nginx -p nginx_local/ -c conf/nginx.conf
