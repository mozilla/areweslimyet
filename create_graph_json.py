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
import re
import gzip

# For looking up build rev numbers
import mercurial
import mercurial.ui
import mercurial.hg
import mercurial.commands
gMercurialRepo = "./mozilla-inbound"

# Config for which tests to export
# - nodeize : [char] split this test's datapoints by the given character and
#             build a tree, otherwise just export them as flat key/values
# - dump    : [bool] dump this test in the per-build data file
# - series  : series to generate plot-lines for.
#      - datapoint : Name of datapoint to dump. If the test is configured above to
#                    'nodeize', you can use a node-name; otherwise you must use a
#                    full datapoint name.
#                    If a list is given, interpret as alternate names for the datapoint
gTests = {
    "Slimtest-TalosTP5-Slow": {
        "nodeize": "/",
        "dump": True,
        "series": {
            "MaxMemoryV2": {
                "datapoint": [
                    "Iteration 5/TabsOpen/Main/explicit",
                    "Iteration 5/TabsOpen/explicit",
                ]
            },
            "MaxMemorySettledV2": {
                "datapoint": [
                    "Iteration 5/TabsOpenSettled/Main/explicit",
                    "Iteration 5/TabsOpenSettled/explicit",
                ]
            },
            "MaxMemoryForceGCV2": {
                "datapoint": [
                    "Iteration 5/TabsOpenForceGC/Main/explicit",
                    "Iteration 5/TabsOpenForceGC/explicit",
                ]
            },
            "MaxMemoryResidentV2": {
                "datapoint": [
                    "Iteration 5/TabsOpen/Main/resident",
                    "Iteration 5/TabsOpen/resident",
                ]
            },
            "MaxMemoryResidentSettledV2": {
                "datapoint": [
                    "Iteration 5/TabsOpenSettled/Main/resident",
                    "Iteration 5/TabsOpenSettled/resident",
                ]
            },
            "MaxMemoryResidentForceGCV2": {
                "datapoint": [
                    "Iteration 5/TabsOpenForceGC/Main/resident",
                    "Iteration 5/TabsOpenForceGC/resident",
                ]
            },
            "StartMemoryV2": {
                "datapoint": [
                    "Iteration 1/Start/Main/explicit",
                    "Iteration 1/Start/explicit",
                ]
            },
            "StartMemoryResidentV2": {
                "datapoint": [
                    "Iteration 1/Start/Main/resident",
                    "Iteration 1/Start/resident",
                ]
            },
            "StartMemorySettledV2": {
                "datapoint": [
                    "Iteration 1/StartSettled/Main/explicit",
                    "Iteration 1/StartSettled/explicit",
                ]
            },
            "StartMemoryResidentSettledV2": {
                "datapoint": [
                    "Iteration 1/StartSettled/Main/resident",
                    "Iteration 1/StartSettled/resident",
                ]
            },
            "EndMemoryV2": {
                "datapoint": [
                    "Iteration 5/TabsClosed/Main/explicit",
                    "Iteration 5/TabsClosed/explicit",
                ]
            },
            "EndMemoryResidentV2": {
                "datapoint": [
                    "Iteration 5/TabsClosed/Main/resident",
                    "Iteration 5/TabsClosed/resident",
                ]
            },
            "EndMemorySettledV2": {
                "datapoint": [
                    "Iteration 5/TabsClosedSettled/Main/explicit",
                    "Iteration 5/TabsClosedSettled/explicit",
                ]
            },
            "EndMemoryForceGCV2": {
                "datapoint": [
                    "Iteration 5/TabsClosedForceGC/Main/explicit",
                    "Iteration 5/TabsClosedForceGC/explicit",
                ]
            },
            "EndMemoryResidentSettledV2": {
                "datapoint": [
                    "Iteration 5/TabsClosedSettled/Main/resident",
                    "Iteration 5/TabsClosedSettled/resident",
                ]
            },
            "EndMemoryResidentForceGCV2": {
                "datapoint": [
                    "Iteration 5/TabsClosedForceGC/Main/resident",
                    "Iteration 5/TabsClosedForceGC/resident",
                ]
            },
            "MaxHeapUnclassifiedV2": {
                "datapoint": [
                    "Iteration 5/TabsOpenSettled/Main/explicit/heap-unclassified",
                    "Iteration 5/TabsOpenSettled/explicit/heap-unclassified",
                ]
            },
            "MaxJSV2": {
                "datapoint": [
                    "Iteration 5/TabsOpenSettled/Main/js-main-runtime",
                    # As of Jul 2012
                    "Iteration 5/TabsOpenSettled/js-main-runtime",
                    # Pre-Jul 2012
                    "Iteration 5/TabsOpenSettled/explicit/js",
                    # Old ~FF4 reporters
                    "Iteration 5/TabsOpenSettled/js",
                    # Brief period in may 2011 before heap-used became explicit
                    "Iteration 5/TabsOpenSettled/heap-used/js"
                ]
            },
            "MaxImagesV2": {
                "datapoint": [
                    "Iteration 5/TabsOpenSettled/Main/explicit/images",
                    "Iteration 5/TabsOpenSettled/explicit/images",
                    # Old ~FF4 reporters
                    "Iteration 5/TabsOpenSettled/images",
                    # Brief period in may 2011 before heap-used became explicit
                    "Iteration 5/TabsOpenSettled/heap-used/images"
                ]
            },

            "Web Content MaxMemoryV2": {"datapoint": "Iteration 5/TabsOpen/Web Content/explicit"},
            "Web Content MaxMemorySettledV2": {"datapoint": "Iteration 5/TabsOpenSettled/Web Content/explicit"},
            "Web Content MaxMemoryForceGCV2": {"datapoint": "Iteration 5/TabsOpenForceGC/Web Content/explicit"},
            "Web Content MaxMemoryResidentV2": {"datapoint": "Iteration 5/TabsOpen/Web Content/resident"},
            "Web Content MaxMemoryResidentSettledV2": {"datapoint": "Iteration 5/TabsOpenSettled/Web Content/resident"},
            "Web Content MaxMemoryResidentForceGCV2": {"datapoint": "Iteration 5/TabsOpenForceGC/Web Content/resident"},
            "Web Content StartMemoryV2": {"datapoint": "Iteration 1/Start/Web Content/explicit"},
            "Web Content StartMemoryResidentV2": {"datapoint": "Iteration 1/Start/Web Content/resident"},
            "Web Content StartMemorySettledV2": {"datapoint": "Iteration 1/StartSettled/Web Content/explicit"},
            "Web Content StartMemoryResidentSettledV2": {"datapoint": "Iteration 1/StartSettled/Web Content/resident"},
            "Web Content EndMemoryV2": {"datapoint": "Iteration 5/TabsClosed/Web Content/explicit"},
            "Web Content EndMemoryResidentV2": {"datapoint": "Iteration 5/TabsClosed/Web Content/resident"},
            "Web Content EndMemorySettledV2": {"datapoint": "Iteration 5/TabsClosedSettled/Web Content/explicit"},
            "Web Content EndMemoryForceGCV2": {"datapoint": "Iteration 5/TabsClosedForceGC/Web Content/explicit"},
            "Web Content EndMemoryResidentSettledV2": {"datapoint": "Iteration 5/TabsClosedSettled/Web Content/resident"},
            "Web Content EndMemoryResidentForceGCV2": {"datapoint": "Iteration 5/TabsClosedForceGC/Web Content/resident"},
            "Web Content MaxHeapUnclassifiedV2": {"datapoint": "Iteration 5/TabsOpenSettled/Web Content/explicit/heap-unclassified"},
            "Web Content MaxJSV2": {"datapoint": "Iteration 5/TabsOpenSettled/Web Content/js-main-runtime"},
            "Web Content MaxImagesV2": {"datapoint": "Iteration 5/TabsOpenSettled/Web Content/explicit/images"}
        }
    },
    "Android-ARMv6": {
        "nodeize": "/",
        "dump": True,
        # See below
        "series": {}
    }
}

# Mapping of unit values to names
unit_map = {
    0: 'bytes',
    1: 'cnt',
    # 2 => UNITS_COUNT_CUMULATIVE, currently this isn't handled
    3: 'pct'
}

# Reuse default tests for android, but s/Iteration 5/Iteration 1/
for k, v in gTests['Slimtest-TalosTP5-Slow']['series'].iteritems():
    # Only use the "Main" entries as a template
    if "Web Content" in k:
        continue

    if type(v['datapoint']) is list:
        out = []
        for x in v['datapoint']:
            out.append(re.sub('^Iteration 5', 'Iteration 1', x))
    else:
        out = re.sub('^Iteration 5', 'Iteration 1', v['datapoint'])
    gTests['Android-ARMv6']['series']['Android' + k] = {"datapoint": out}


# Python 2 compat
if sys.hexversion < 0x03000000:
    def bytes(string, **kwargs):
        return string


def error(msg):
    sys.stderr.write(msg + '\n')
    sys.exit(1)

if len(sys.argv) != 4:
    error("Usage: %s <database> <seriesname> <outdir>" % sys.argv[0])

gDatabase = os.path.normpath(sys.argv[1])
gSeriesName = sys.argv[2]
gOutDir = os.path.normpath(sys.argv[3])

if not os.path.isfile(gDatabase):
    error("Database '%s' not found" % gDatabase)

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

sql = sqlite3.connect(gDatabase, timeout=900)
sql.row_factory = sqlite3.Row
cur = sql.cursor()

# Fetch and sort the builds by timestamp. For builds with identical push dates,
# lookup the revision number from hg
cur.execute('''SELECT build.id as `id`, build.name as `name`, build.time as `time`, repo.name as `repo_name`
               FROM `benchtester_builds` as build, `benchtester_repos` as repo
               WHERE build.repo_id = repo.id''')

builds = cur.fetchall()
hg_ui = None
hg_repo = None


def build_sort(build_a, build_b):
    global hg_repo, hg_ui
    if build_a['time'] != build_b['time']:
        return 1 if build_a['time'] > build_b['time'] else -1
    # Builds have equal timestamp, look up their revision number in repo if
    # possible
    if not hg_repo:
        hg_ui = mercurial.ui.ui()
        hg_repo = mercurial.hg.repository(hg_ui, gMercurialRepo)
        hg_ui.readconfig(os.path.join(gMercurialRepo, ".hg", "hgrc"))
        hg_ui.pushbuffer()
        # Pull repo, but don't update so we don't conflict with whatever the test
        # daemon is doing with it
        mercurial.commands.pull(hg_ui, hg_repo, check=False, update=False)
        hg_ui.popbuffer()

    # Get revisions
    try:
        hg_ui.pushbuffer()
        mercurial.commands.log(
            hg_ui, hg_repo, rev=["%s" % (build_a['name'],)], template="{rev}", date="", user=None, follow=None)
        a_rev = int(hg_ui.popbuffer())
        hg_ui.pushbuffer()
        mercurial.commands.log(
            hg_ui, hg_repo, rev=["%s" % (build_b['name'],)], template="{rev}", date="", user=None, follow=None)
        b_rev = int(hg_ui.popbuffer())
    except Exception as e:
        # mercurial throws all kinds of fun exceptions for bad input
        print("WARNING: Couldn't lookup ordering of commits with identical timestamp: %s / %s (%s: %s)" %
              (build_a[1], build_b[1], type(e), e))
        return 0

    print("Builds %s and %s have identical timestamp, using rev numbers %u and %u" %
          (build_a['name'], build_b['name'], a_rev, b_rev))
    return 1 if a_rev > b_rev else -1 if b_rev > a_rev else 0

print("Sorting builds...")
builds = sorted(builds, cmp=build_sort)

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
    'series': dict((n, []) for n in gSeriesNames),
    'builds': []
}

# Open the old file, if possible, to skip generating redundant data
old_data = None
old_series_file = os.path.join(gOutDir, gSeriesName + '.json.gz')
if os.path.exists(old_series_file):
    last_series = gzip.open(old_series_file, 'r')
    old_data = json.loads(last_series.read())
    last_series.close()
    # Old builds by index
    old_builds_map = {}
    for i in range(len(old_data["builds"])):
        old_builds_map[old_data["builds"][i]["revision"]] = i

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

i = 0
for build in builds:
    i += 1

    # Lookup tests for this build
    testdata = {}
    for testname in gTests.keys():
        testdata[testname] = {'time': None, 'id': None, 'nodes': {}}

        # Get latest test for this build
        cur.execute('''SELECT id, time FROM benchtester_tests
                   WHERE name = ? AND build_id = ? AND successful = 1
                   ORDER BY time DESC LIMIT 1''', [testname, build['id']])
        testrow = cur.fetchone()
        if not testrow:
            continue

        testdata[testname]['time'] = testrow['time']
        testdata[testname]['id'] = testrow['id']

    test_ids = [testdata[testname]['id'] for testname in gTests.keys()]

    #
    # Determine if we should process this build or use the existing data
    #
    if old_data and build['name'] in old_builds_map and old_data['builds'][old_builds_map[build['name']]]['test_ids'] == test_ids:
        print("[%u/%u] Using existing data for build %s" % (i, len(builds), build['name']))
        oldindex = old_builds_map[build['name']]
        data['builds'].append(old_data['builds'][oldindex])
        for sname in gSeriesNames:
            if sname in old_data['series']:
                data['series'][sname].append(old_data['series'][sname][oldindex])
            else:
                # Fill null in for newly-added series. We'll regenerate these by hand
                # if desired, but forcing-regenerate means we have to de-archive all
                # old DBs when the datapoint may only be in recent tests anyway
                data['series'][sname].append(None)
    else:
        print("[%u/%u] Processing build %s" % (i, len(builds), build['name']))
        # Fill builds
        data['builds'].append(
            {'revision': build['name'], 'time': build['time'], 'test_ids': test_ids})

        #
        # For each test gTests references, pull all of its data into testdata
        #
        for testname in gTests.keys():
            if testname in gTests:
                nodeize = gTests[testname].get('nodeize')
            else:
                nodeize = False

            # Pull all data for latest run of this test on this build
            allrows = cur.execute('''SELECT dp.name AS datapoint,
                                      c.name AS checkpoint,
                                      p.name AS process,
                                      d.iteration, d.value, d.units, d.kind
                               FROM benchtester_data d,
                                    benchtester_datapoints dp,
                                    benchtester_procs p,
                                    benchtester_checkpoints c
                               WHERE test_id = ? AND dp.id = d.datapoint_id
                                                 AND c.id = d.checkpoint_id
                                                 AND p.id = d.proc_id
                            ''', [testdata[testname]['id']])

            # NB: For now kind is ignored

            # Sort data, splitting it up into nodes if requested. Calculate the value
            # of each node - either a sum of its childnodes, or its explicit value if
            # given. The idea is to reduce the amount of data juggling the frontend
            # needs to do.
            for row in allrows:
                datapoint = row['datapoint']
                units = unit_map.get(row['units'])
                if not units:
                    print("skipping unhandled unit %s for %s" % (row['units'], datapoint))
                    continue

                # Prefix the reporter name, e.g. "Iteration 1/StartSettled/Main/<reporter>" so
                # that it fits nicely into a tree.
                datapoint = "Iteration %u/%s/%s/%s" % (row['iteration'], row['checkpoint'], row['process'], datapoint)

                if nodeize:
                    # Note that we preserve null values as 'none', to differentiate missing
                    # data from values of 0
                    cursor = testdata[testname]['nodes']
                    thisnode = datapoint.split(nodeize)
                    for n in range(len(thisnode)):
                        leaf = thisnode[n]
                        cursor.setdefault(leaf, {})
                        cursor = cursor[leaf]
                        # Nodes can have a value *and* childnodes, so we set _val for specific
                        # values, and _sum for derived childnodes
                        if n == len(thisnode) - 1:
                            cursor['_units'] = units
                            cursor['_val'] = row['value']

                        # discard() will make this the canonical units if no explicit value
                        # for this node shows up.
                        if '_childunits' in cursor and cursor['_childunits'] != units:
                            cursor['_childunits'] = 'mixed'
                        else:
                            cursor['_childunits'] = units

                        if not '_sum' in cursor or cursor['_sum'] == None:
                            cursor['_sum'] = row['value']
                        elif row['value'] != None:
                            cursor['_sum'] += row['value']
                else:
                    # Flat data
                    # For types with units, we use [ 'unit', val ] pairs
                    val = [units, row['value']] if units else row['value']
                    testdata[testname]['nodes'][row['datapoint']] = val

        # Discard duplicate _sum/_val data after totalling, flatten node if there
        # are no children
        def discard(node):
            # If no explicit value or units, use the sum/childunits
            if '_val' not in node:
                node['_val'] = node.get('_sum')
            if '_units' not in node:
                node['_units'] = node.get('_childunits')
            if '_sum' in node:
                del node['_sum']
            if '_childunits' in node:
                del node['_childunits']
            # Bytes is the default unit
            if node.get('_units') == 'bytes':
                del node['_units']
            for x in node:
                if x not in ['_val', '_units']:
                    discard(node[x])
                    # Just _val, no _units or _sum, replace node with just raw value
                    if len(node[x]) == 1:
                        node[x] = node[x]['_val']
        for x in testdata:
            discard(testdata[x]['nodes'])

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
                    elif type(node) in [int, long]:
                        value = node
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
            else:
              # Add test metadata.
              testdata[testname]['repo'] = build['repo_name']
              testdata[testname]['revision'] = build['name']

        #
        # Write out the test data for this build into <buildname>.json.gz
        #
        testfile = gzip.open(os.path.join(gOutDir, build['name'] + '.json.gz'), 'w', 9)
        testfile.write(bytes(json.dumps(testdata, indent=2), encoding="utf-8"))
        testfile.write(bytes('\n', encoding="utf-8"))
        testfile.close()

data['generated'] = time.time()
data['series_info'] = {}
for test in gTests.keys():
    for series in gTests[test]['series'].keys():
        data['series_info'][series] = gTests[test]['series'][series]
        data['series_info'][series]['test'] = test

print("[%u/%u] Finished, writing %s.json.gz" % (i, i, gSeriesName))
# Write out all the generated series into series.json.gz
datafile = gzip.open(os.path.join(gOutDir, gSeriesName + '.json.gz'), 'w', 9)
datafile.write(bytes(json.dumps(data, indent=2), encoding="utf-8"))
datafile.write(bytes('\n', encoding="utf-8"))
datafile.close()
