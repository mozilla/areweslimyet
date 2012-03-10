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
  mode = form['mode'].value if 'mode' in form else None
  start = form['startbuild'].value if 'startbuild' in form else None
  end = form['endbuild'].value if 'endbuild' in form else None
  prioritize = form['prioritize'].value if 'prioritize' in form else None

  if not start or not mode:
    error("startbuild and mode are required")
  if mode == "compile":
    error("Temporarily disabled")
  if mode not in [ 'nightly', 'tinderbox', 'compile' ]:
    error("Unknown mode")

  invalid = re.compile("[^a-zA-Z0-9\-]")
  if invalid.match(start) or (end and invalid.match(end)):
    error("Invalid input")

  ret = "--mode \"%s\" --startbuild \"%s\"" % (mode, start)
  if end:
    ret = "%s --lastbuild \"%s\"" % (ret, end)
  if prioritize:
    ret = "%s --prioritize" % (ret,)

  reqname = "%s.webrequest" % int(time.time())
  f = open(os.path.join("batch", reqname), 'w')
  f.write("%s\n" % (ret,))
  f.close()
  finish({ 'result': 'success', 'reqname': reqname })
  
try:
  main()
except Exception, e:
  error("Request triggered an exception :: %s: %s" % (type(e), e))
