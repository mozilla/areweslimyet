#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import ConfigParser
import gzip
import hashlib
import json
import math
import os
import socket
import sys
import tempfile
import time
import uuid

import boto
import boto.s3.connection

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


# Based on autophone implementation
class S3:
    def __init__(self, bucket_name, access_key_id, access_secret_key):
        """
        Opens an S3 connection to the given bucket.
        Can raise KeyError, boto.exception.NoAuthHandlerFound, boto.exception.S3ResponseError.
        """
        conn = boto.s3.connection.S3Connection(access_key_id, access_secret_key)
        if not conn.lookup(bucket_name):
            raise KeyError('bucket %s not found' % bucket_name)
        self.bucket = conn.get_bucket(bucket_name)

    def upload(self, path, destination):
        """
        Uploads a file to the S3 bucket.
        Can raise boto.exception.S3ResponseError.
        """

        key = self.bucket.get_key(destination)
        if not key:
            key = self.bucket.new_key(destination)

        ext = os.path.splitext(path)[-1]
        if ext in ('.log', '.txt'):
            key.set_metadata('Content-Type', 'text/plain')

        with tempfile.NamedTemporaryFile('w+b', suffix=ext) as tf:
            with gzip.GzipFile(path, 'wb', fileobj=tf) as gz:
                with open(path, 'rb') as f:
                    gz.writelines(f)
            tf.flush()
            tf.seek(0)
            key.set_metadata('Content-Encoding', 'gzip')
            key.set_contents_from_file(tf)

        return key.generate_url(expires_in=0, query_auth=False)


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


def upload_artifact(s3, fname, key, lname):
    """
    Uploads an artifact to S3 and returns a job description entry for it.

    :param s3: The S3 instance to use to upload.
    :param fname: The path to the file to be uploaded.
    :param key: The key for the uploaded file in S3.
    :param lname: The name to use for the link in the job description.
    """
    try:
        url = s3.upload(fname, key)
        return {
            'url': url,
            'value': lname,
            'content_type': 'link',
            'title': 'artifact uploaded'
        }
    except Exception, e:
        err_str = 'Failed to upload artifact %s: %s' % (fname, e)
        print err_str
        return {
            'value': err_str,
            'content_type': 'text',
            'title': 'Error'
        }


def create_treeherder_job(repo, revision, client, nodes, s3=None):
    """
    Creates a treeherder job for the given set of data.

    :param repo: The repository this build came from.
    :param revision: The mercurial revision of the build.
    :param client: The TreeherderClient to use.
    :param nodes: The dataset for this build.
    :param s3: Optional Amazon S3 bucket to upload logs to.
    """
    rev_hash = client.get_resultsets(repo, revision=revision)[0]['revision_hash']

    tj = TreeherderJob()
    tj.add_tier(2)
    tj.add_revision_hash(rev_hash)
    tj.add_project(repo)

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
    perf_data = json.dumps({ 'performance_data': perf_blob })
    tj.add_artifact('performance_data', 'json', perf_data)

    # Set the job guid to a combination of the revision and the job data. This
    # gives us a reasonably unique guid, but is also reproducible for the same
    # set of data.
    job_guid = hashlib.sha1(revision + perf_data)
    tj.add_job_guid(job_guid.hexdigest())

    # If an S3 connection is provided the logs for this revision are uploaded.
    # Addtionally a 'Job Info' blob is built up with links to the logs that
    # will be displayed in the 'Job details' pane in treeherder.
    if s3:
        job_details = []

        # To avoid overwriting existing data (perhaps if a job is retriggered)
        # the job guid is included in the key.
        log_prefix = "%s/%s/%s" % (repo, revision, job_guid.hexdigest())

        # Add the test log.
        log_id = '%s/%s' % (log_prefix, 'awsy_test_raw.log')
        job_detail = upload_artifact(s3, 'logs/%s.test.log' % revision,
                                     log_id, 'awsy_test.log')
        if 'url' in job_detail:
            # The test log is the main log and will be linked to the log
            # viewer and raw log icons in treeherder.
            tj.add_log_reference('test.log', job_detail['url'])
        job_details.append(job_detail)

        # Add the gecko log.
        log_id = '%s/%s' % (log_prefix, 'gecko.log')
        job_detail = upload_artifact(s3, "logs/%s.gecko.log" % revision,
                                     log_id, 'gecko.log')
        job_details.append(job_detail)

        tj.add_artifact('Job Info', 'json', { 'job_details': job_details })

    return tj


def post_treeherder_jobs(client, revisions, s3=None):
    """
    Processes each file and submits a treeherder job with the data from each file.

    :param client: The TreeherderClient to use.
    :param revisions: A dictionary of revisions and their associated data.
    :param s3: Optional Amazon S3 bucket to upload logs to.
    """
    successful = []
    for (revision, test_set) in revisions.iteritems():
        nodes = test_set['nodes']
        repo = test_set.get('repo', 'mozilla-inbound')

        tjc = TreeherderJobCollection()
        try:
            tjc.add(create_treeherder_job(repo, revision, client, nodes, s3))
        except KeyError as e:
            print "Failed to generate data for %s: %s, probably still running" % (revision, e)
            continue

        try:
            # NB: In theory we could batch these, but each collection has to be from
            #     the same repo and it's possible we have different repos in our
            #     dataset.
            client.post_collection(repo, tjc)
            #print tjc.to_json()

            successful.append(revision)
            print "Submitted perf data for %s to %s" % (revision, client.host)
        except Exception as e:
            print "Failed to submit data for %s: %s" % (revision, e)

    return successful


def filter_datasets(file_names, perf_history_file='last_perf.json'):
    """
    Retrieves a dictionary of datasets that should be processed. Filters out
    revisions that have already been posted.

    :param file_names: List of potential json files to process.
    :param perf_history_file: The file that contains the last revisions
     submitted.
    """

    try:
        with open(perf_history_file, 'r') as f:
            known_builds_list = json.load(f)
    except:
        known_builds_list = []

    known_builds = set(known_builds_list)

    revisions = {}

    for name in file_names:
        # Attempt to filter prior to unarchiving.
        revision = os.path.basename(name).split('.')[0]
        if len(revision) == 40 and revision in known_builds:
            print "Skipping known revision %s" % revision
            continue

        with gzip.open(name) as f:
            data = json.load(f)

        test_set = data['Slimtest-TalosTP5-Slow']

        # Attempt to retrieve the revision from the metadata, otherwise parse
        # it from the file name which has the form <revision>.json.gz
        if 'revision' in test_set:
            revision = test_set['revision']

        # Check if we've already processed this build.
        if revision in known_builds:
            print "Skipping known revision %s" % revision
            continue

        known_builds_list.append(revision)
        revisions[revision] = test_set

    return revisions


def process_datasets(host, client_id, secret, revisions, s3):
    # For local testing just http is used, otherwise https is required.
    if host != 'local.treeherder.mozilla.org':
        protocol = 'https'
    else:
        protocol = 'http'

    client = TreeherderClient(protocol=protocol, host=host, client_id=client_id, secret=secret)
    return post_treeherder_jobs(client, revisions, s3)


def update_known_revisions(new_revisions, perf_history_file='last_perf.json'):
    """
    Update the list of known revisions.
    """
    try:
        with open(perf_history_file, 'r') as f:
            known_builds_list = json.load(f)
    except:
        known_builds_list = []

    known_builds_list += new_revisions

    try:
        with open(perf_history_file, 'w') as f:
            # Write out the last 100 revisions
            json.dump(known_builds_list[-100:], f)
    except Exception, e:
      print "WARNING: Unable to write revision file: %s" % e


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        print "Usage: process_perf_data.py config_file files..."
        sys.exit(1)

    # Determine which revisions we need to process.
    file_names = args[1:]
    revisions = filter_datasets(file_names)
    if not revisions:
        print "No new revisions to process."
        sys.exit(0)

    # Load the config.
    cfg = ConfigParser.ConfigParser()
    cfg.read(args[0])
    host = cfg.get('treeherder', 'host')
    client_id = cfg.get('treeherder', 'client_id')
    secret = cfg.get('treeherder', 'client_secret')

    # Attempt to load the S3 module if credentials are provided.
    s3 = None
    try:
        s3_bucket = cfg.get('S3', 'bucket')
        s3_access_key_id = cfg.get('S3', 'access_key_id')
        s3_access_secret_key = cfg.get('S3', 'access_secret_key')
        s3 = S3(s3_bucket, s3_access_key_id, s3_access_secret_key)
    except Exception, e:
        print "S3 Failed: %s" % e

    # Push the data to the production treeherder instance.
    successful = process_datasets(host, client_id, secret, revisions, s3)
    update_known_revisions(successful)

    # Try to push data to staging as well.
    try:
        host = cfg.get('treeherder_staging', 'host')
        client_id = cfg.get('treeherder_staging', 'client_id')
        secret = cfg.get('treeherder_staging', 'client_secret')

        process_datasets(host, client_id, secret, revisions, s3)
    except:
        pass

    sys.exit(0)
