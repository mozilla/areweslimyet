#!/usr/bin/env python

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
  path = val('path')

  if not start or not mode:
    error("startbuild and mode are required")

  if mode not in [ 'nightly', 'tinderbox', 'compile', 'ftp' ]:
    error("Unknown mode")

  invalid = re.compile("[^a-zA-Z0-9\-]")
  if invalid.match(series) invalid.match(start) or (end and invalid.match(end)):
    error("Invalid input")

  ret = { "mode": mode }
  if mode == "ftp":
    ret['path'] = path
  else:
    ret['firstbuild'] = start

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
