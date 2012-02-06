#!/usr/bin/env python

# Right now:
# pull the most recent test for each build (usually only one),
# Pull selected datapoints for that test

import sys
import os
import sqlite3
import json
import time
import gzip

if len(sys.argv) != 3:
  sys.stderr.write("Usage: %s <database> <outfile>\n" % sys.argv[0])
  sys.exit(1)

gDatabase = sys.argv[1]
gOutDir = sys.argv[2]

if not os.path.isdir(gOutDir):
  sys.stderr.write("Directory %s does not exist\n" % gOutDir)
  sys.exit(1)

gSeriesInfo = {
  "MaxMemory" : {
    "test": "Slimtest-TalosTP5",
    "datapoint": "Iteration 4.TabsOpen.mem.explicit/"
  },
  "MaxMemoryResident" : {
    "test": "Slimtest-TalosTP5",
    "datapoint": "Iteration 4.TabsOpen.mem.resident"
  },
  "StartMemory" : {
    "test": "Slimtest-TalosTP5",
    "datapoint": "Iteration 0.PreTabs.mem.explicit/"
  },
  "StartMemoryResident" : {
    "test": "Slimtest-TalosTP5",
    "datapoint": "Iteration 0.PreTabs.mem.resident"
  },
  "EndMemory" : {
    "test": "Slimtest-TalosTP5",
    "datapoint": "Iteration 4.TabsClosed.mem.explicit/"
  },
  "EndMemoryResident" : {
    "test": "Slimtest-TalosTP5",
    "datapoint": "Iteration 4.TabsClosed.mem.resident"
  },
}

sql = sqlite3.connect(gDatabase)
sql.row_factory = sqlite3.Row
cur = sql.cursor()

cur.execute('''SELECT `id`, `name`, `time` FROM `benchtester_builds` ORDER BY `time` ASC''')
builds = cur.fetchall()

# Test names referenced in one or more series
test_names = set(map(lambda x: x['test'], gSeriesInfo.values()))

# series - a dict of series name (e.g. StartMemory) -> [[x,y], [x2, y2], ...]
#          All series have the same length, such the same index in any series
#          refers to the same build
# build_info - a list with the same length/order as the series that contains
#              info about this build
# test_info - A dict of lists indexed by testname (e.g. Slimtest-TalosTP5)
#             with the same length/order as the series, containing a full dump
#             of test data for each build (many series can reference the same
#             test). This data is saved separately per build/test, and XHR'd in
#             when desired.
data = {
  'series' : dict((n, []) for n in gSeriesInfo.keys()),
  'build_info' : []
}

i = 0

# Open the old file, if possible, to skip generating redundant data
try:
  last_series = gzip.open(os.path.join(gOutDir, 'series.json.gz'), 'r')
  old_data = json.loads(last_series.read())
  in_old_data = True
except Exception:
  in_old_data = False

for build in builds:
  i += 1
  if in_old_data and (
    old_data['build_info'][i - 1]['revision'] != build['name']
    or not os.path.exists(os.path.join(gOutDir, build['name'] + '.json.gz'))):
    in_old_data = False
  
  if in_old_data:
    print("[%u/%u] Using existing data for build %s" % (i, len(builds), build['name'])) 
    data['build_info'].append(old_data['build_info'][i - 1])
    for sname, sinfo in gSeriesInfo.iteritems():
      data['series'][sname].append(old_data['series'][sname][i - 1])
  else:
    print("[%u/%u] Processing build %s" % (i, len(builds), build['name']))
    test_ids = {}
    # Fill build_info
    data['build_info'].append({ 'id' : build['id'], 'revision' : build['name'] })
    
    testdata = {}
    
    # For each test a series references, pull all data into testdata
    for testname in test_names:
      # Pull all data for latest run of this test on this build
      allrows = cur.execute('''SELECT d.datapoint, d.value, t.time, t.id
                              FROM benchtester_data d
                              JOIN benchtester_tests t ON d.test_id = t.id
                              LEFT JOIN benchtester_tests t2 ON t.name = t2.name AND t.build_id = t2.build_id AND t.time < t2.time
                              WHERE t.name = ? AND t2.id IS NULL AND t.build_id = ? AND t.id IS NOT NULL
                              ''', [testname, build['id']])
      testdata[testname] = { 'time' : None, 'id' : None, 'allvalues' : {} };
      for row in allrows:
        if not testdata[testname]['time']:
          testdata[testname]['time'] = row['time']
          testdata[testname]['id'] = row['id']
        testdata[testname]['allvalues'][row['datapoint']] = row['value']
      
    # Build all series from testdata
    for sname, sinfo in gSeriesInfo.iteritems():
      thisinfo = testdata[sinfo['test']]['allvalues']
      
      if sinfo['datapoint'][-1:] == '/':
        value = reduce(lambda val, (k, v): val + v if k.startswith(sinfo['datapoint']) and v else val, thisinfo.iteritems(), 0)
      else:
        value = thisinfo[sinfo['datapoint']] if thisinfo.has_key(sinfo['datapoint']) else 0
      data['series'][sname].append([build['time'], value])
      
    # Write out the test data for this build
    testfile = gzip.open(os.path.join(gOutDir, build['name'] + '.json.gz'), 'w', 9)
    json.dump(testdata, testfile, indent=2)
    testfile.write('\n')
    testfile.close()

data['info'] = { 'generated' : time.time() }

datafile = gzip.open(os.path.join(gOutDir, 'series.json.gz'), 'w', 9)
json.dump(data, datafile, indent=2)
datafile.write('\n')
datafile.close()
