#!/usr/bin/env python2

import os
import sys
import cgi
import json
import re
import time

form = cgi.FieldStorage()

def error(text):
  finish({ "result": "failure", "error": text })

def finish(obj):
  print("Content-Type: application/json; charset=utf-8\n\n")
  print(json.dumps(obj))
  sys.exit(0)

def main():
  def val(n):
    return form[n].value if n in form else None
  mode = val('mode')
  start = val('startbuild')
  end = val('endbuild')
  note = val('note')
  series = val('series')

  invalidBuild = re.compile("[^a-zA-Z0-9\-]")
  invalidSeries = re.compile("[^a-z0-9_]")
  if not mode or not start \
        or (series and invalidSeries.search(series)) \
        or (mode != "ftp" and start and invalidBuild.search(start)) \
        or (end and invalidBuild.search(end)):
    error("Invalid input")

  if mode not in [ 'nightly', 'tinderbox', 'compile', 'ftp' ]:
    error("Unknown mode")


  if series and series.startswith("areweslimyet"):
    error("Series names may not start with areweslimyet")

  if mode == "ftp" and not series:
    error("FTP builds must use a custom series")

  if mode == "ftp" and not (start.startswith('/pub') or start.startswith('try:')):
    error("Invalid ftp path");

  ret = { "mode": mode, "firstbuild": start }
  if series:
    ret['series'] = series
  if note:
    ret['note'] = note
  if end:
    ret['lastbuild'] = end
  if val('prioritize'):
    ret['prioritize'] = True
  if val('force'):
    ret['force'] = True

  reqname = "%s.webrequest" % int(time.time())
  f = open(os.path.join("batch", reqname), 'w')
  json.dump(ret, f)
  f.close()
  finish({ 'result': 'success', 'reqname': reqname })

try:
  main()
except Exception, e:
  error("Request triggered an exception :: %s: %s" % (type(e), e))
