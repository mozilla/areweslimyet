#!/usr/bin/env python

# For all builds in given sqlite db, finds the newest test run of that test and:
# - Generate series.json.gz with all the series in gSeries, ready for graphing
# - Generate a <buildname>.json.gz with all datapoints from the tests configured
#   for dumping in gTests

import sys
import os
import sqlite3
import json
import time
import gzip

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
  if not os.path.isdir(parentdir):
    error("'%s' is not a directory, cannot create folders in it" % parentdir)
  os.mkdir(gOutDir)

# Extra config for specific tests. (not required to use a test in gSeries)
# - nodeize : [char] split this test's datapoints by the given character and
#             build a tree, otherwise just export them as flat key/values
# - dump    : [bool] dump this test in the per-build data file
gTests = {
  "Slimtest-TalosTP5" : {
    "nodeize" : "/",
    "dump" : True
  }
}

# Series to generate plot-lines for.
# - test      : Name of test to look at
# - datapoint : Name of datapoint to dump. If the test is configured above to
#               'nodeize', you can use a node-name; otherwise you must use a
#               full datapoint name
# - use_sum   : *If* this test is nodeized, always use the sum of this node,
#               even if it has an explicit value
gSeries = {
  "MaxMemory" : {
    "test": "Slimtest-TalosTP5",
    "datapoint": "Iteration 5.TabsOpen.mem.explicit"
  },
  "MaxMemorySettled" : {
    "test": "Slimtest-TalosTP5",
    "datapoint": "Iteration 5.TabsOpenSettled.mem.explicit"
  },
  "MaxMemoryForceGC" : {
    "test": "Slimtest-TalosTP5",
    "datapoint": "Iteration 5.TabsOpenForceGC.mem.explicit"
  },
  "MaxMemoryResident" : {
    "test": "Slimtest-TalosTP5",
    "datapoint": "Iteration 5.TabsOpen.mem.resident"
  },
  "MaxMemoryResidentSettled" : {
    "test": "Slimtest-TalosTP5",
    "datapoint": "Iteration 5.TabsOpenSettled.mem.resident"
  },
  "MaxMemoryResidentForceGC" : {
    "test": "Slimtest-TalosTP5",
    "datapoint": "Iteration 5.TabsOpenForceGC.mem.resident"
  },
  "StartMemory" : {
    "test": "Slimtest-TalosTP5",
    "datapoint": "Iteration 1.Start.mem.explicit"
  },
  "StartMemoryResident" : {
    "test": "Slimtest-TalosTP5",
    "datapoint": "Iteration 1.Start.mem.resident"
  },
  "StartMemorySettled" : {
    "test": "Slimtest-TalosTP5",
    "datapoint": "Iteration 1.StartSettled.mem.explicit"
  },
  "StartMemoryResidentSettled" : {
    "test": "Slimtest-TalosTP5",
    "datapoint": "Iteration 1.StartSettled.mem.resident"
  },
  "EndMemory" : {
    "test": "Slimtest-TalosTP5",
    "datapoint": "Iteration 5.TabsClosed.mem.explicit"
  },
  "EndMemoryResident" : {
    "test": "Slimtest-TalosTP5",
    "datapoint": "Iteration 5.TabsClosed.mem.resident"
  },
  "EndMemorySettled" : {
    "test": "Slimtest-TalosTP5",
    "datapoint": "Iteration 5.TabsClosedSettled.mem.explicit"
  },
  "EndMemoryResidentSettled" : {
    "test": "Slimtest-TalosTP5",
    "datapoint": "Iteration 5.TabsClosedSettled.mem.resident"
  },
}

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
data = {
  'series' : dict((n, []) for n in gSeries.keys()),
  'builds' : []
}

i = 0

# Open the old file, if possible, to skip generating redundant data
try:
  last_series = gzip.open(os.path.join(gOutDir, 'series.json.gz'), 'r')
  old_data = json.loads(last_series.read())
except Exception:
  old_data = None

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
    for sname, sinfo in gSeries.items():
      data['series'][sname].append(old_data['series'][sname][i - 1])
  else:
    print("[%u/%u] Processing build %s" % (i, len(builds), build['name']))
    test_ids = {}
    # Fill builds
    data['builds'].append({ 'revision' : build['name'], 'time' : build['time'] })
    
    testdata = {}
    
    #
    # For each test gSeries or gTests references, pull all of its data into testdata
    #
    for testname in set(gTests.keys()) | \
                    set(map(lambda x: x['test'], gSeries.values())):
      # Pull all data for latest run of this test on this build
      allrows = cur.execute('''SELECT d.datapoint, d.value, t.time, t.id
                              FROM benchtester_data d
                              JOIN benchtester_tests t ON d.test_id = t.id
                              LEFT JOIN benchtester_tests t2 ON t.name = t2.name AND t.build_id = t2.build_id AND t.time < t2.time
                              WHERE t.name = ? AND t2.id IS NULL AND t.build_id = ? AND t.id IS NOT NULL
                              ''', [testname, build['id']])
      testdata[testname] = { 'time' : None, 'id' : None, 'nodes' : {} };
      
      for row in allrows:
        testdata[testname].setdefault('time', row['time'])
        testdata[testname].setdefault('id', row['id'])
        
        if testname in gTests and gTests[testname].get('nodeize'):
          # Nodeize.
          # Note that we perserve null values as 'none', to differentiate missing data from values of 0
          cursor = testdata[testname]['nodes']
          thisnode = row['datapoint'].split(gTests[testname]['nodeize'])
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
    for sname, sinfo in gSeries.items():
      nodes = testdata[sinfo['test']]['nodes']
      
      if sinfo['test'] in gTests and gTests[sinfo['test']].get('nodeize'):
        # Nodeized data, find this node
        node = nodes
        for branch in sinfo['datapoint'].split(gTests[sinfo['test']].get('nodeize')):
          if node and branch in node:
            node = node[branch]
          else:
            node = None
        
        if node == None:
          value = None
        elif sinfo.get('use_sum') or not '_val' in node:
          value = node.get('_sum')
        else:
          value = node.get('_val')
      else:
        # Flat data
        value = nodes.get(sinfo['datapoint'])
        
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
data['series_info'] = gSeries

print("[%u/%u] Finished, writing series.json.gz" % (i, i))
# Write out all the generated series into series.json.gz
datafile = gzip.open(os.path.join(gOutDir, 'series.json.gz'), 'w', 9)
datafile.write(bytes(json.dumps(data, indent=2), encoding="utf-8"))
datafile.write(bytes('\n', encoding="utf-8"))
datafile.close()
