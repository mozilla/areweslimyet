#!/usr/bin/env python

import os
import sys
import ftplib
import time
import re
import socket

socket.setdefaulttimeout(30)

def fail(err):
  sys.stderr.write("%s\n" % err)
  sys.exit(1)
def stat(msg):
  sys.stdout.write("%s\n" % msg)
  
if len(sys.argv) != 2:
  fail("Requires one argument: Date (YYYY-MM-DD)")

ts = time.strptime(sys.argv[1], "%Y-%m-%d")
day = ts.tm_mday
month = ts.tm_mon
year = ts.tm_year

stat("Looking up nightly for %s/%s, %s" % (month, day, year))

#
# Connect, CD to this month's dir
#
ftp = ftplib.FTP('ftp.mozilla.org')
ftp.login()
ftp.voidcmd('CWD /pub/firefox/nightly/%i/%02i/' % (year, month))

# 
# Find the appropriate YYYY-MM-DD-??-mozilla-central directory. There may be
# multiple if the builds took over an hour
#

nightlydirs = []
def findnightlydir(line):
  global nightlydirs
  x = line.split('-')
  if x[-2:] == [ 'mozilla', 'central' ] and int(x[0]) == year and int(x[1]) == month and int(x[2]) == day:
    nightlydirs.append(line)

rawlist = ftp.retrlines('NLST', findnightlydir)

if not len(nightlydirs):
  fail("Failed to find any nightly directory for that date :(")

stat("Nightly directories are: %s" % ', '.join(nightlydirs))

#
# Find the linux-x86_64 .txt file to see what this was built against
# (nightlies might be built against different commits if something
#  landed while building, so we randomly pick the linux64 one)
#

def checknightlydir(dirname):
  global infofile
  stat("Checking directory %s" % dirname)
  infofile = False
  def findinfofile(line):
    global infofile
    if line.endswith('.txt'):
      infofile = line
  
  ftp.voidcmd('CWD %s' % dirname)
  ftp.retrlines('NLST', findinfofile)
  if not infofile:
    ftp.voidcmd('CwD ..')
  return infofile

for x in nightlydirs:
  infofile = checknightlydir(x)
  if infofile: break

if not infofile:
  fail("Couldn't find any directory with info on this build :(")

#
# read and parse info file
#

filedat = False
def readfile(line):
  global filedat
  if filedat:
    filedat = "%s\n%s" % (filedat, line)
  else:
    filedat = line

ftp.retrlines('RETR %s' % infofile, readfile)
stat("Got build info: %s" % filedat)

m = re.search('[0-9]{14}', filedat)
timestamp = int(time.mktime(time.strptime(m.group(0), '%Y%m%d%H%M%S')))
m = re.search('([0-9a-zA-Z]{12})( |$)', filedat)
rev = m.group(1)

print("%s\n%s" % (rev, timestamp))