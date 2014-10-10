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

files = list(filter(lambda x: x != seriesname + '.json.gz' and x.startswith(seriesname + "-") and x.endswith('.json.gz'), os.listdir(outdir)))
files.sort()

print("Merging %u files: %s" % (len(files), files))

totaldata = { 'builds' : [], 'series' : {}, 'series_info' : {}, 'allseries' : [] }

# Hard-coded to condensed by day below
totaldata['condensed'] = 60 * 60 * 24;

# Returns the timestamp of this build's day @ midnight UTC
def dayof(timestamp):
  return int(calendar.timegm(datetime.datetime.utcfromtimestamp(timestamp).date().timetuple()))

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
      if cday != -1: ranges.append((start, i - 1))
      cday = day
      start = i
  ranges.append((start, len(data['builds']) - 1))

  for point in ranges:
    build = {}
    build['firstrev'] = data['builds'][point[0]]['revision']
    build['time'] = data['builds'][point[0]]['time']
    if point[0] != point[1]:
      build['time'] = dayof(build['time'])
      build['count'] = point[1] - point[0] + 1
      build['lastrev'] = data['builds'][point[1]]['revision']
      build['timerange'] = [ data['builds'][point[0]]['time'], data['builds'][point[1]]['time'] ]

    cdata['builds'].append(build)

    for sname in data['series'].keys():
      series = data['series'][sname][point[0]:point[1] + 1]
      iseries = filter(lambda x: x is not None, series)
      cdata['series'].setdefault(sname, [])
      if len(iseries) == 0:
        cdata['series'][sname].append(None)
      else:
        iseries.sort()
        if len(iseries) % 2 == 1:
          median = iseries[(len(iseries) - 1) / 2]
        else:
          median = iseries[len(iseries) / 2]
        if iseries[0] == median:
          cdata['series'][sname].append(median)
        else:
          cdata['series'][sname].append([iseries[0], median, iseries[-1]])
  return cdata

for fname in files:
  print("Condensing %s" % (fname,))
  f = gzip.open(os.path.join(outdir, fname), 'r')
  fdata = json.loads(f.read())
  f.close()
  if not len(fdata['builds']): continue
  totaldata['allseries'].append({
      'fromtime' : fdata['builds'][0]['time'],
      'totime' : fdata['builds'][-1]['time'],
      'dataname' : fname.replace('.json.gz', '')
    })
  cdata = condense_data(fdata)
  for x in cdata['series'].keys():
    totaldata['series'].setdefault(x, [])
    # If this series just appeared, or was absent from some datafiles before this,
    # make sure we pad out with nulls to keep the indexes lined up
    totaldata['series'][x].extend([None for y in range(len(totaldata['builds']) - len(totaldata['series'][x]))])
    totaldata['series'][x].extend(cdata['series'][x])
  # Continue pad out series that dont exist in this file
  for x in totaldata['series'].keys():
    if x not in cdata['series']:
      totaldata['series'][x].extend([None for y in range(len(cdata['builds'])) ])
  totaldata['builds'].extend(cdata['builds'])
  totaldata['series_info'].update(fdata['series_info'])

  # Sanity check this, logic bugs here cause massively bogus data
  for x in totaldata['series'].keys():
    a = len(totaldata['builds'])
    b = len(totaldata['series'][x])
    if a != b:
      sys.stderr.write("Error series %s does not match build count: %u builds vs %u datapoints" % (x, a, b))
      sys.exit(1)

totaldata['generated'] = time.time()

print("Writing %s.json.gz" % (seriesname,))
datafile = gzip.open(os.path.join(outdir, seriesname + '.json.gz'), 'w', 9)
datafile.write(bytes(json.dumps(totaldata, indent=2), encoding="utf-8"))
datafile.write(bytes('\n', encoding="utf-8"))
datafile.close()

print("Done")
