#!/usr/bin/env python2

import sys
import os
import subprocess

# Simple hook for ./run_slimtest that starts a VNC server for each worker
# and kills it afterwards

def before(build, buildnum):
  global display
  display = ":%u" % (buildnum + 9,)
  try: subprocess.check_output([ "vncserver", "-kill", display ])
  except: pass
  subprocess.check_output([ "vncserver", display ])
  os.environ['DISPLAY'] = display

def after():
  global display
  subprocess.check_output([ "vncserver", "-kill", display ])
