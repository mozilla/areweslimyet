#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2012 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

# For all builds in given sqlite db, finds the newest test run of that test and:
# - Generate series.json.gz with all the series in gTests, ready for graphing
# - Generate a <buildname>.json.gz with all datapoints from the tests configured
#   for dumping in gTests

import sys
import os
import sqlite3
import json
import time
import gzip

# Config for which tests to export
# - nodeize : [char] split this test's datapoints by the given character and
#             build a tree, otherwise just export them as flat key/values
# - dump    : [bool] dump this test in the per-build data file
# - series  : series to generate plot-lines for.
#      - datapoint : Name of datapoint to dump. If the test is configured above to
#                    'nodeize', you can use a node-name; otherwise you must use a
#                    full datapoint name.
#                    If a list is given, interpret as alternate names for the datapoint
#      - use_sum   : *If* this test is nodeized, always use the sum of this node,
#                    even if it has an explicit value
gTests = {
  "Slimtest-TalosTP5" : {
    "nodeize" : "/",
    "dump" : True,
    "series" : {
      "MaxMemory" : { "datapoint": "Iteration 5/TabsOpen/explicit" },
      "MaxMemorySettled" : { "datapoint": "Iteration 5/TabsOpenSettled/explicit" },
      "MaxMemoryForceGC" : { "datapoint": "Iteration 5/TabsOpenForceGC/explicit" },
      "MaxMemoryResident" : { "datapoint": "Iteration 5/TabsOpen/resident" },
      "MaxMemoryResidentSettled" : { "datapoint": "Iteration 5/TabsOpenSettled/resident" },
      "MaxMemoryResidentForceGC" : { "datapoint": "Iteration 5/TabsOpenForceGC/resident" },
      "StartMemory" : { "datapoint": "Iteration 1/Start/explicit" },
      "StartMemoryResident" : { "datapoint": "Iteration 1/Start/resident" },
      "StartMemorySettled" : { "datapoint": "Iteration 1/StartSettled/explicit" },
      "StartMemoryResidentSettled" : { "datapoint": "Iteration 1/StartSettled/resident" },
      "EndMemory" : { "datapoint": "Iteration 5/TabsClosed/explicit" },
      "EndMemoryResident" : { "datapoint": "Iteration 5/TabsClosed/resident" },
      "EndMemorySettled" : { "datapoint": "Iteration 5/TabsClosedSettled/explicit" },
      "EndMemoryResidentSettled" : { "datapoint": "Iteration 5/TabsClosedSettled/resident" },
      "MaxHeapUnclassified" : { "datapoint": "Iteration 5/TabsOpenSettled/explicit/heap-unclassified" },
      "MaxJS" : {
        "datapoint": [
          "Iteration 5/TabsOpenSettled/explicit/js",
          # Old ~FF4 reporters
          "Iteration 5/TabsOpenSettled/js",
          # Brief period in may 2011 before heap-used became explicit
          "Iteration 5/TabsOpenSettled/heap-used/js"
        ],
      },
      "MaxImages" : {
        "datapoint": [
          "Iteration 5/TabsOpenSettled/explicit/images",
          # Old ~FF4 reporters
          "Iteration 5/TabsOpenSettled/images",
          # Brief period in may 2011 before heap-used became explicit
          "Iteration 5/TabsOpenSettled/heap-used/images"
        ]
      }
    }
  },
  "Slimtest-TalosTP5-Slow" : {
    "nodeize" : "/",
    "dump" : True,
    "series" : {
      "MaxMemoryV2" : { "datapoint": "Iteration 5/TabsOpen/explicit" },
      "MaxMemorySettledV2" : { "datapoint": "Iteration 5/TabsOpenSettled/explicit" },
      "MaxMemoryForceGCV2" : { "datapoint": "Iteration 5/TabsOpenForceGC/explicit" },
      "MaxMemoryResidentV2" : { "datapoint": "Iteration 5/TabsOpen/resident" },
      "MaxMemoryResidentSettledV2" : { "datapoint": "Iteration 5/TabsOpenSettled/resident" },
      "MaxMemoryResidentForceGCV2" : { "datapoint": "Iteration 5/TabsOpenForceGC/resident" },
      "StartMemoryV2" : { "datapoint": "Iteration 1/Start/explicit" },
      "StartMemoryResidentV2" : { "datapoint": "Iteration 1/Start/resident" },
      "StartMemorySettledV2" : { "datapoint": "Iteration 1/StartSettled/explicit" },
      "StartMemoryResidentSettledV2" : { "datapoint": "Iteration 1/StartSettled/resident" },
      "EndMemoryV2" : { "datapoint": "Iteration 5/TabsClosed/explicit" },
      "EndMemoryResidentV2" : { "datapoint": "Iteration 5/TabsClosed/resident" },
      "EndMemorySettledV2" : { "datapoint": "Iteration 5/TabsClosedSettled/explicit" },
      "EndMemoryResidentSettledV2" : { "datapoint": "Iteration 5/TabsClosedSettled/resident" },
      "MaxHeapUnclassifiedV2" : { "datapoint": "Iteration 5/TabsOpenSettled/explicit/heap-unclassified" },
      "MaxJSV2" : {
        "datapoint": [
          "Iteration 5/TabsOpenSettled/explicit/js",
          # Old ~FF4 reporters
          "Iteration 5/TabsOpenSettled/js",
          # Brief period in may 2011 before heap-used became explicit
          "Iteration 5/TabsOpenSettled/heap-used/js"
        ]
      },
      "MaxImagesV2" : {
        "datapoint": [
          "Iteration 5/TabsOpenSettled/explicit/images",
          # Old ~FF4 reporters
          "Iteration 5/TabsOpenSettled/images",
          # Brief period in may 2011 before heap-used became explicit
          "Iteration 5/TabsOpenSettled/heap-used/images"
        ]
      }
    }
  }
}

# Python 2 compat
if sys.hexversion < 0x03000000:
  def bytes(string, **kwargs):
    return string

def error(msg):
  sys.stderr.write(msg + '\n')
  sys.exit(1)

if len(sys.argv) != 3:
  error("Usage: %s <database> <outdir>" % sys.argv[0])

gDatabase = os.path.normpath(sys.argv[1])
gOutDir = os.path.normpath(sys.argv[2])

if not os.path.isfile(gDatabase):
  error("Database '%s' not found")

if not os.path.isdir(gOutDir):
  if os.path.exists(gOutDir):
    error("File '%s' is not a directory" % gOutDir)
  # Try to create
  parentdir = os.path.dirname(gOutDir)
  # dirname() returns '' for this-directory. Other os.path functions dont
  # recognize '' as this-directory. ???.
  if parentdir == '':
    parentdir = '.'
  if not os.path.isdir(parentdir):
    error("'%s' is not a directory, cannot create folders in it" % parentdir)
  os.mkdir(gOutDir)

sql = sqlite3.connect(gDatabase)
sql.row_factory = sqlite3.Row
cur = sql.cursor()

cur.execute('''SELECT `id`, `name`, `time` FROM `benchtester_builds` ORDER BY `time` ASC''')
builds = cur.fetchall()

# series - a dict of series name (e.g. StartMemory) -> [[x,y], [x2, y2], ...]
#          All series have the same length, such the same index in any series
#          refers to the same build
# builds - a list with the same length/order as the series that contains
#              info about this build
# test_info - A dict of lists indexed by testname (e.g. Slimtest-TalosTP5)
#             with the same length/order as the series, containing a full dump
#             of test data for each build (many series can reference the same
#             test). This data is saved separately per build/test, and XHR'd in
#             when desired.

gSeriesNames = [y for x in gTests.values() for y in x['series'].keys()]

data = {
  'series' : dict((n, []) for n in gSeriesNames),
  'builds' : []
}

i = 0

# Open the old file, if possible, to skip generating redundant data
try:
  last_series = gzip.open(os.path.join(gOutDir, 'series.json.gz'), 'r')
  old_data = json.loads(last_series.read())
except Exception:
  old_data = None

# Helper to find a node by datapoint
def _findNode(nodes, datapoint, nodeize):
  node = nodes
  if nodeize:
    for branch in datapoint.split(nodeize):
      if node and branch in node:
        node = node[branch]
      else:
        return None
    return node
  else:
    return nodes.get(datapoint)
  
for build in builds:
  i += 1
  #
  # Determine if we should process this build or use the existing data
  #
  if old_data and (
      len(old_data['builds']) >= i
      and old_data['builds'][i - 1]['revision'] == build['name']
      and os.path.exists(os.path.join(gOutDir, build['name'] + '.json.gz'))):
    print("[%u/%u] Using existing data for build %s" % (i, len(builds), build['name'])) 
    data['builds'].append(old_data['builds'][i - 1])
    for sname in gSeriesNames:
      data['series'][sname].append(old_data['series'][sname][i - 1])
  else:
    print("[%u/%u] Processing build %s" % (i, len(builds), build['name']))
    test_ids = {}
    # Fill builds
    data['builds'].append({ 'revision' : build['name'], 'time' : build['time'] })
    
    testdata = {}
    
    #
    # For each test gTests references, pull all of its data into testdata
    #
    for testname in gTests.keys():

      testdata[testname] = { 'time' : None, 'id' : None, 'nodes' : {} }

      # Get latest test for this build
      cur.execute('''SELECT id, time FROM benchtester_tests
                     WHERE name = ? AND build_id = ?
                     ORDER BY time DESC LIMIT 1''', [testname, build['id']])
      testrow = cur.fetchone()
      if not testrow:
        continue

      testdata[testname]['time'] = testrow['time']
      testdata[testname]['id'] = testrow['id']

      if testname in gTests:
        nodeize = gTests[testname].get('nodeize')
      else:
        nodeize = False

      # Pull all data for latest run of this test on this build
      allrows = cur.execute('''SELECT datapoint, value
                               FROM benchtester_data d
                               WHERE test_id = ?
                            ''', [testrow['id']])

      # Sort data, splitting it up into nodes if requested
      for row in allrows:
        if nodeize:
          # Note that we perserve null values as 'none', to differentiate missing data from values of 0
          cursor = testdata[testname]['nodes']
          thisnode = row['datapoint'].split(nodeize)
          for n in range(len(thisnode)):
            leaf = thisnode[n]
            cursor.setdefault(leaf, {})
            cursor = cursor[leaf]
            # Nodes can have a value *and* childnodes, so we set _val for specific
            # values, and _sum for derived childnodes
            if n == len(thisnode) - 1:
              cursor['_val'] = row['value']

            if not '_sum' in cursor or cursor['_sum'] == None:
              cursor['_sum'] = row['value']
            elif row['value'] != None:
              cursor['_sum'] += row['value']
        else:
          # Flat data
          testdata[testname]['nodes'][row['datapoint']] = row['value']
    
    #
    # Build all series [[x,y], ...] from testdata object
    #
    for test, testinfo in gTests.items():
      for sname, sinfo in testinfo['series'].items():
        nodes = testdata[test]['nodes']
        # Is this nodeized data?
        nodeize = gTests[test].get('nodeize')

        node = None
        if type(sinfo['datapoint']) == list:
          datapoint = None
          # If datapoint has alternate names, find the first one defined in the
          # nodes
          for dp in sinfo['datapoint']:
            node = _findNode(nodes, dp, nodeize)
            if node:
              break
        else:
          node = _findNode(nodes, sinfo['datapoint'], nodeize)

        if nodeize:
          if node == None:
            value = None
          elif sinfo.get('use_sum') or not '_val' in node:
            value = node.get('_sum')
          else:
            value = node.get('_val')
        else:
          # Flat data
          value = node

        data['series'][sname].append(value)
    
    #
    # Discard data for tests not requested to be dumped
    #
    for testname in testdata.keys():
      if not testname in gTests.keys() or \
         not gTests[testname].get('dump'):
        del testdata[testname]
    
    #
    # Write out the test data for this build into <buildname>.json.gz
    #
    testfile = gzip.open(os.path.join(gOutDir, build['name'] + '.json.gz'), 'w', 9)
    testfile.write(bytes(json.dumps(testdata, indent=2), encoding="utf-8"))
    testfile.write(bytes('\n', encoding="utf-8"))
    testfile.close()

data['generated'] = time.time()
data['test_info'] = gTests

print("[%u/%u] Finished, writing series.json.gz" % (i, i))
# Write out all the generated series into series.json.gz
datafile = gzip.open(os.path.join(gOutDir, 'series.json.gz'), 'w', 9)
datafile.write(bytes(json.dumps(data, indent=2), encoding="utf-8"))
datafile.write(bytes('\n', encoding="utf-8"))
datafile.close()
