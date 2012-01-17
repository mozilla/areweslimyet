#!/usr/bin/env python

# Right now:
# pull the most recent test for each build (usually only one),
# Pull selected datapoints for that test

import sys
import os
import sqlite3
import json
import time

if len(sys.argv) != 3:
  sys.stderr.write("Usage: %s <database> <outfile>\n" % sys.argv[0])
  sys.exit(1)

gDatabase = sys.argv[1]
gOutfile = sys.argv[2]

gPullData = {
  "MaxMemory" : {
    "test": "Slimtest-Talos2.1-Standalone",
    "datapoint": "Iteration 4.TabsOpen.mem.resident" ,
    "nicename": "Fresh Start Resident Memory",
  },
  "StartMemory" : {
    "test": "Slimtest-Talos2.1-Standalone",
    "datapoint": "Iteration 0.Start iteration.mem.resident" ,
    "nicename": "Fresh Start Resident Memory",
  },
  "EndMemory" : {
    "test": "Slimtest-Talos2.1-Standalone",
    "datapoint": "Iteration 4.End iteration.mem.resident" ,
    "nicename": "Fresh Start Resident Memory",
  },
}

sql = sqlite3.connect(gDatabase)
cur = sql.cursor()
cur.row_factory = sqlite3.Row

cur.execute('''SELECT `id`, `name`, `time` FROM `benchtester_builds` ORDER BY `time` ASC''')
builds = cur.fetchall()

test_names = set(map(lambda x: x['test'], gPullData.values()))

data = {}

for build in builds:
  test_ids = {}
  for n in test_names:
    # Find ID of latest testrun for this test on this build
    cur.execute('''SELECT * FROM `benchtester_tests` WHERE `name` = ? AND `build_id` = ? ORDER BY `time` ASC LIMIT 1''', [n, build['id']])
    test_ids[n] = cur.fetchone()['id']
  
  # Pull data
  for dname,dinfo in gPullData.items():
    cur.execute('''SELECT * FROM `benchtester_data` WHERE `test_id` = ? AND datapoint LIKE ?''', [test_ids[dinfo['test']], dinfo['datapoint']])
    row = cur.fetchone()
    value = 0
    while row:
      if row['value']:
        value += row['value']
      else:
        print("Warning: Null Value for datapoint '%s' for test %u" % (row['datapoint'], test_ids[dinfo['test']]))
      row = cur.fetchone()
    if value:
      if not data.has_key(dname): data[dname] = []
      data[dname].append({ 'build': build['name'], 'time': build['time'], 'value': value})

datafile = open(gOutfile, 'w')
datafile.write("// Generated %s\n\n" % time.strftime("%b %d, %Y @ %I:%M%p %Z"))
datafile.write("var gSlimGraphSeries = ")
json.dump(data, datafile, indent=2)
datafile.write(';\n')
