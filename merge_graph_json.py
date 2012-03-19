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

# Python 2 compat
if sys.hexversion < 0x03000000:
  def bytes(string, **kwargs):
    return string

if len(sys.argv) != 2:
  sys.stderr.write("Usage: %s outdir\n" % sys.argv[0])
  sys.exit(1)

outdir = sys.argv[1]
os.listdir(outdir)

files = list(filter(lambda x: x.endswith('-condensed.json.gz'), os.listdir(outdir)))

print("Merging %u files: %s" % (len(files), files))

totaldata = { 'builds' : [], 'series' : {}, 'series_info' : {} }

for fname in files:
  f = gzip.open(os.path.join(outdir, fname), 'r')
  fdata = json.loads(f.read())
  f.close()
  totaldata['builds'].extend(fdata['builds'])
  for x in fdata['series'].keys():
    totaldata['series'].setdefault(x, [])
    totaldata['series'][x].extend(fdata['series'][x])
  totaldata['series_info'].update(fdata['series_info'])

totaldata['generated'] = time.time()

print("Writing series.json.gz")
datafile = gzip.open(os.path.join(outdir, 'series.json.gz'), 'w', 9)
datafile.write(bytes(json.dumps(totaldata, indent=2), encoding="utf-8"))
datafile.write(bytes('\n', encoding="utf-8"))
datafile.close()

print("Done")
