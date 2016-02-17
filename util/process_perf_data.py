#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import ConfigParser
import gzip
import json
import math
import os
import socket
import sys
import time
import uuid

from thclient import (TreeherderClient, TreeherderJob,
                      TreeherderJobCollection, TreeherderArtifactCollection)

# A description of each checkpoint and the root path to it.
CHECKPOINTS = [
    { 'name': "Fresh start", 'path': "Iteration 1/Start" },
    { 'name': "Fresh start [+30s]", 'path': "Iteration 1/StartSettled" },
    { 'name': "After tabs open", 'path': "Iteration 5/TabsOpen" },
    { 'name': "After tabs open [+30s]", 'path': "Iteration 5/TabsOpenSettled" },
    { 'name': "After tabs open [+30s, forced GC]", 'path': "Iteration 5/TabsOpenForceGC" },
    { 'name': "Tabs closed", 'path': "Iteration 5/TabsClosed" },
    { 'name': "Tabs closed [+30s]", 'path': "Iteration 5/TabsClosedSettled" },
    { 'name': "Tabs closed [+30s, forced GC]", 'path': "Iteration 5/TabsClosedForceGC" }
]

# A description of each perfherder suite and the path to its values.
PERF_SUITES = [
    { 'name': "Resident Memory", 'node': "resident" },
    { 'name': "Explicit Memory", 'node': "explicit" },
    { 'name': "Heap Unclassified", 'node': "explicit/heap-unclassified" },
    { 'name': "JS", 'node': "js-main-runtime" },
    { 'name': "Images", 'node': "explicit/images" }
]

def get_node_value(datapoint, nodes):
    """
    Retrieves a nested value from the nodes dictionary.

    :param nodes: A dictionary of nested value nodes. Each node either has a
                 '_val' entry which is the sum of its child nodes, or if it is
                 a leaf node the entry itself is the value.

                 Example structure:
                  {
                      'explicit': {
                          '_val': 678,
                          'images': {
                              '_val': 678,
                              'image 1': 400,
                              'image 2': 278
                          }
                      },
                      'js-main-runtime': 897
                  }
    :param datapoint: A path to the desired value.
    """
    for branch in datapoint.split('/'):
        if nodes and branch in nodes:
            nodes = nodes[branch]
        else:
            raise KeyError("Datapoint not found: %s" % datapoint)

    if type(nodes) in [int, long]:
        return nodes
    else:
        return nodes.get('_val')


def create_suite(name, node, data):
    """
    Creates a suite suitable for adding to a perfherder blob. Calculates the
    geometric mean of the checkpoint values and adds that to the suite as
    well.

    :param name: The name of the suite.
    :param node: The path of the data node to extract data from.
    :param data: The dataset to retrieve data from.
    """
    suite = {
        'name': name,
        'subtests': [],
        'lowerIsBetter': True,
        'units': 'bytes'
    }

    total = 0
    for checkpoint in CHECKPOINTS:
        subtest = {
            'name': checkpoint['name'],
            'value': get_node_value('/'.join([ checkpoint['path'], node ]), data),
            'lowerIsBetter': True,
            'units': 'bytes'
        }
        suite['subtests'].append(subtest);
        total += math.log(subtest['value'])

    # Add the geometric mean. For more details on the calculation see:
    #   https://en.wikipedia.org/wiki/Geometric_mean#Relationship_with_arithmetic_mean_of_logarithms
    suite['value'] = math.exp(total / len(CHECKPOINTS))

    return suite


def create_perf_data(nodes):
    """
    Builds up a performance data blob suitable for submitting to perfherder.
    """
    perf_blob = {
        'framework': { 'name': 'awsy' },
        'suites': []
    }

    for suite in PERF_SUITES:
        perf_blob['suites'].append(create_suite(suite['name'], suite['node'], nodes))

    return perf_blob


def create_treeherder_job(repo, revision, client, nodes):
    """
    Creates a treeherder job for the given set of data.

    :param repo: The repository this build came from.
    :param revision: The mercurial revision of the build.
    :param client: The TreeherderClient to use.
    :param nodes: The dataset for this build.
    """
    rev_hash = client.get_resultsets(repo, revision=revision)[0]['revision_hash']

    tj = TreeherderJob()
    tj.add_tier(2)
    tj.add_revision_hash(rev_hash)
    tj.add_project(repo)
    tj.add_job_guid(str(uuid.uuid4()))

    tj.add_job_name('awsy 1')
    tj.add_job_symbol('a1')
    tj.add_group_name('awsy')
    tj.add_group_symbol('AWSY')

    tj.add_product_name('firefox')
    tj.add_state('completed')
    tj.add_result('success')
    submit_timestamp = int(time.time())
    tj.add_submit_timestamp(submit_timestamp)
    tj.add_start_timestamp(submit_timestamp)
    tj.add_end_timestamp(submit_timestamp)
    tj.add_machine(socket.getfqdn())

    tj.add_build_info('linux', 'linux64', 'x86_64')
    tj.add_machine_info('linux', 'linux64', 'x86_64')
    tj.add_option_collection({'opt': True})

    perf_blob = create_perf_data(nodes)
    tj.add_artifact('performance_data', 'json', json.dumps({ 'performance_data': perf_blob }))

    return tj


def post_treeherder_jobs(client, fileNames, perf_history_file='last_perf.json'):
    """
    Processes each file and submits a treeherder job with the data from each file.

    :param client: The TreeherderClient to use.
    :param fileNames: The files to process.
    :param perf_history_file: The file that contains the last revisions
     submitted.
    """

    try:
        with open(perf_history_file, 'r') as f:
            known_builds_list = json.load(f)
    except:
        known_builds_list = []

    known_builds = set(known_builds_list)

    for name in fileNames:
        with gzip.open(name) as f:
            data = json.load(f)

        test_set = data['Slimtest-TalosTP5-Slow']

        nodes = test_set['nodes']
        repo = test_set.get('repo', 'mozilla-inbound')
        # Attempt to retrieve the revision from the metadata, otherwise parse
        # it from the file name which has the form <revision>.json.gz
        if 'revision' in test_set:
            revision = test_set['revision']
        else:
            revision = os.path.basename(name).split('.')[0]

        # Check if we've already processed this build.
        if revision in known_builds:
            print "Skipping known revision %s" % revision
            continue

        tjc = TreeherderJobCollection()
        try:
            tjc.add(create_treeherder_job(repo, revision, client, nodes))
        except KeyError as e:
            print "Failed to generate data for %s: %s" % (revision, e)
            continue

        # NB: In theory we could batch these, but each collection has to be from
        #     the same repo and it's possible we have different repos in our
        #     dataset.
        client.post_collection(repo, tjc)
        #print tjc.to_json()

        known_builds_list.append(revision)

    try:
        with open(perf_history_file, 'w') as f:
            # Write out the last 100 revisions
            json.dump(known_builds_list[-100:], f)
    except:
        pass


def process_datasets(host, client_id, secret, fileNames):
    client = TreeherderClient(protocol='https', host=host, client_id=client_id, secret=secret)
    post_treeherder_jobs(client, fileNames)


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        print "Usage: process_perf_data.py config_file files..."
        sys.exit(1)

    cfg = ConfigParser.ConfigParser()
    cfg.read(args[0])
    host = cfg.get('treeherder', 'host')
    client_id = cfg.get('treeherder', 'client_id')
    secret = cfg.get('treeherder', 'client_secret')
    fileNames = args[1:]

    process_datasets(host, client_id, secret, fileNames)
