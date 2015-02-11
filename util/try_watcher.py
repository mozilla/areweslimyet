# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import ConfigParser
import json
import os
import re
import sys
import tempfile
import time
import traceback
import urllib
import urllib2

import requests

from mozillapulse.consumers import NormalizedBuildConsumer
from mozillapulse.config import PulseConfiguration

AWSY_ENDPOINT = "http://arcus.corp.mtv2.mozilla.com:8000/status/request.cgi"
PUSHLOG_ENDPOINT = "https://hg.mozilla.org/try/json-pushes"

gBatchDir = None


def run(args=sys.argv[1:]):
    if not args:
        print "usage: try_watcher.py config_file.cfg [batch_dir]"
        return 1

    if len(args) > 1:
        gBatchDir = args[1]
        if not os.path.exists(gBatchDir):
            print "invalid batch dir specified"
            return 1

    pulse_args = {
        # A string to identify this consumer when logged into pulse.mozilla.org
        'applabel': 'try-build-consumer-persisted',

        # Each message contains a topic. Only messages that match the topic specified here will
        # be delivered. '#' is a wildcard, so this topic matches all messages that start with
        # 'build.try.linux64.opt.'.
        'topic': 'build.try.linux64.opt.#',

        # Durable queues will store messages inside pulse even if your consumer goes offline for
        # a bit. Otherwise, any messages published while the consumer is not explicitly
        # listening will be lost forever. Keep it set to False for testing purposes.
        'durable': True,

        # A callback that will get invoked on each build event.
        'callback': on_build_event,
    }

    # user and password must be specified in the config file
    cfg = ConfigParser.ConfigParser()
    cfg.read(args[0])
    pulse_args['user'] = cfg.get("pulse", "user")
    pulse_args['password'] = cfg.get("pulse", "password")

    pulse = NormalizedBuildConsumer(**pulse_args)

    while True:
        try:
            pulse.listen()
        except KeyboardInterrupt:
            raise
        except IOError:
            # Sometimes there is a socket timeout. Just call listen again; this
            # is fairly common and not worth logging.
            pass
        except:
            # It is possible for rabbitmq to throw other exceptions. Just log
            # them and move on.
            traceback.print_exc()


def http_json_request(url, params=None, post=False):
    """
    GETs or POSTs to a http json endpoint.

    :param url: The endpoint to connect to.
    :param params: A dictionary of query string paramaters.
    :param post: Indicates whether or not a POST should be performed.
    """
    data = None
    log_url = url
    if params:
        encoded_params = urllib.urlencode(params)
        log_url += "?" + encoded_params
        if post:
            data = encoded_params
        else:
            url = log_url

    method = "POST" if post else "GET"
    print "%s - %s" % (method, log_url)

    result = None
    try:
        response = urllib2.urlopen(url, data, timeout=30)
        raw = response.read()
        result = json.loads(raw)
    except (IOError, urllib2.URLError) as e:
        print "Failed to access %s: %s - %s" % (log_url, type(e), e)
    except ValueError as e:
        print "Invalid JSON returned from server: %s" % raw

    return result


def queue_try_job(rev, series):
    """
    Queues up an awsy run for the given try revision.

    :param rev: The revision of the try push.
    :param series: Name for the series to graph the try push in.
    """
    params = {
        'mode': 'try',
        'startbuild': rev[:12],
        'series': series,
        'prioritize': True
    }

    result = http_json_request(AWSY_ENDPOINT, params, post=True)
    if not result:
        return

    if result['result'] == 'success':
        print 'Queued try request for %s to %s series' % (rev, series)
    else:
        print 'Failed to queue try request for %s to %s series: %s' % (rev, series, result['error'])


def write_try_job(rev, series, batch_dir):
    """Writes the try job to the given directory"""
    params = {
        'mode': 'try',
        'firstbuild': rev[:12],
        'series': series,
        'prioritize': True
    }

    with tempfile.NamedTemporaryFile(
            mode='w', suffix='.tryrequest',
            dir=batch_dir, delete=False) as f:
        json.dump(params, f)


def sanitize_name(series):
    """
    Sanitize the name. It must be lowercase and consist of alphanumeric
    characters and underscores.
    """
    original = series

    series = series.lower()
    if series.startswith("areweslimyet"):
        print "Invalid series name: %s" % series
        return None

    # Replace invalid characters with '_'
    sanitize_regex = re.compile("[^a-z0-9_]")
    series = sanitize_regex.sub('_', series)

    if series != original:
        print "Sanitized series name from %s to %s" % (original, series)

    return series


def get_series_name(rev):
    """
    Retrieves the awsy series for the provided revision.

    :param rev: The revision to check.
    """
    params = {
        'changeset': rev,
        'full': 1
    }

    pushlog = http_json_request(PUSHLOG_ENDPOINT, params)
    if not pushlog:
        return None

    changesets = pushlog[pushlog.keys()[0]]['changesets']
    commit = next((x['desc'] for x in changesets if x['node'].startswith(rev)), None)
    if not commit:
        print "Changeset not found for revision"
        from pprint import pprint
        pprint(changesets)
        return None

    try_header = next((line for line in commit.splitlines() if 'try:' in line), None)
    if not try_header:
        print "try message not found in commit"
        print commit
        return None

    print try_header
    m = re.search(r'-awsy\s+(\S+)', try_header)
    if not m:
        return None

    return sanitize_name(m.group(1))


def on_build_event(data, message):
    message.ack()

    payload = data['payload']
    routing_key = data['_meta']['routing_key']
    revision = payload['revision']

    print 'key: %s' % routing_key
    print '  Got a %s job' % (payload['key'],)
    print '  status: %d' % payload['status']
    print '  revision: %s' % revision

    series_name = get_series_name(revision)
    if series_name:
        print "AWSY run requested for %s in the %s series" % (revision, series_name)
        if gBatchDir:
            write_try_job(revision, series_name, gBatchDir)
        else:
            queue_try_job(revision, series_name)


if __name__ == '__main__':
    sys.exit(run())
