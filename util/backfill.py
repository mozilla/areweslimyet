#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import datetime
import json
import tempfile
import time


def parse_arg_date(date_str):
    return datetime.datetime.strptime(date_str, '%Y-%m-%d')


def parse_command_line():
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true', default=False,
        help='Run tests even if they have already been run.')
    parser.add_argument('start_date', type=parse_arg_date,
        help='Date to start running from. Format: YYYY-MM-DD')
    parser.add_argument('end_date', nargs='?', type=parse_arg_date, default=None,
        help='Date to stop running. Optional, defaults to 1 day after start date.')
    parser.add_argument('--batch-dir', default='html/status/batch',
        help='Directory to write the batch request to.')

    cmdline = parser.parse_args()
    if not cmdline.end_date:
        cmdline.end_date = cmdline.start_date + datetime.timedelta(1)

    return cmdline


def queue_request(start_date, end_date, force, batch_dir, verbose=False):
    """
    Queues a batch request to run tests against a given date range.

    :param start_date: The beginning of a date range to run tests against.
    :param end_date: The end of a date range to run tests against.
    :param force: Whether or not to force rerunning of the tests.
    :param batch_dir: Where to write the batch request.
    """

    request = {
        'mode': 'tinderbox',
        'firstbuild': time.mktime(start_date.timetuple()),
        'lastbuild': time.mktime(end_date.timetuple()),
        'force': force,
        'note': 'Backfilling %s - %s' % (start_date, end_date)
    }

    if verbose:
        import pprint
        pprint.pprint(request)

    with tempfile.NamedTemporaryFile(
            mode='w', suffix='.backfill',
            dir=batch_dir, delete=False) as f:
        json.dump(request, f)


if __name__ == '__main__':
    cmdline = parse_command_line()
    queue_request(cmdline.start_date, cmdline.end_date,
                  cmdline.force, cmdline.batch_dir)
