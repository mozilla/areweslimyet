#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2012 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

# Merges the given list of blah-condensed.json.gz files into the master
# series.json.gz file

import os
import sys
import time
import gzip
import json
import datetime
import calendar

# Python 2 compat
if sys.hexversion < 0x03000000:
  def bytes(string, **kwargs):
    return string

if len(sys.argv) != 3:
  sys.stderr.write("Usage: %s <seriesname> <datadir>\n" % sys.argv[0])
  sys.exit(1)

seriesname = sys.argv[1]
outdir = sys.argv[2]
os.listdir(outdir)

files = list(filter(lambda x: x != seriesname + '.json.gz' and x.startswith(seriesname) and x.endswith('.json.gz'), os.listdir(outdir)))

print("Merging %u files: %s" % (len(files), files))

totaldata = { 'builds' : [], 'series' : {}, 'series_info' : {},  }

# Returns the timestamp of this build's day @ midnight UTC
def dayof(timestamp):
  return int(calendar.timegm(datetime.date.fromtimestamp(timestamp).timetuple()))

def condense_data(data):
  cdata = {
    'builds': [],
    'series' : {}
  }
  cday = -1
  ranges = []
  start = 0
  for i in range(len(data['builds'])):
    day = dayof(data['builds'][i]['time'])
    if day != cday:
      if cday != -1: ranges.append((start, i))
      cday = day

  for point in ranges:
    build = {}
    build['firstrev'] = data['builds'][point[0]]['revision']
    build['lastrev'] = data['builds'][point[1]]['revision']
    build['time'] = dayof(data['builds'][point[0]]['time'])

    cdata['builds'].append(build)

    for sname in data['series'].keys():
      series = data['series'][sname][point[0]:point[1]]
      iseries = filter(lambda x: x is not None, series)
      cdata['series'].setdefault(sname, [])
      if len(iseries) == 0:
        cdata['series'][sname].append([ None, None, None ])
      else:
        iseries.sort()
        if len(series) % 2 == 1:
          median = iseries[(len(iseries) - 1) / 2]
        else:
          median = int(round(float(iseries[len(iseries) / 2] + iseries[len(iseries) / 2 - 1])/2, 0))
        cdata['series'][sname].append([iseries[0], median, iseries[-1]])
  return cdata

for fname in files:
  print("Condensing %s" % (fname,))
  f = gzip.open(os.path.join(outdir, fname), 'r')
  fdata = json.loads(f.read())
  f.close()
  cdata = condense_data(fdata)
  totaldata['builds'].extend(cdata['builds'])
  for x in cdata['series'].keys():
    totaldata['series'].setdefault(x, [])
    totaldata['series'][x].extend(cdata['series'][x])
  totaldata['series_info'].update(fdata['series_info'])

totaldata['generated'] = time.time()

print("Writing %s.json.gz" % (seriesname,))
datafile = gzip.open(os.path.join(outdir, seriesname + '.json.gz'), 'w', 9)
datafile.write(bytes(json.dumps(totaldata, indent=2), encoding="utf-8"))
datafile.write(bytes('\n', encoding="utf-8"))
datafile.close()

print("Done")
