#!/bin/bash

# Copyright © 2012 Mozilla Corporation

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

# Utility script to test every Xth nightly since 2010
step="$1"
skip="$2"
[ ! -z "$step" ] || step=1
[ ! -z "$skip" ] || skip=0

set -e

>test_months.err

starttime=$(date +%s)

year=2011
while [ $year -le 2012 ]; do
  month=1
  while [ $month -le 12 ]; do
    day=1
    while [ $day -le 31 ]; do
      # Break if this month doesn't have this many days (feb: this year)
      # Or if in future
      timestamp=$(date +%s --date="$month/$day $year" 2>/dev/null || true)
      if [ -z "$timestamp" ] || [ $timestamp -gt $starttime ]; then break; fi
      
      if [ "$skip" -eq 0 ]; then
        skip=$step
        
        [ $day -ge 10 ] && nday=$day || nday="0$day"
        [ $month -ge 10 ] && nmonth=$month || nmonth="0$month"
        
        datestr="$year-$nmonth-$nday"
        echo ":: Testing $datestr" | tee -a test_months.log
        if ! (./test_nightly.sh "$datestr" | tee test_months.tmp); then
          echo "!! Test failed for $month/$day, $year: $(cat test_months.tmp)" | tee -a test_months.log
        fi
        
      fi
      
      skip=$(( skip - 1 ))
      day=$(( day + 1 ))
    done
    month=$(( month + 1 ))
  done
  year=$(( year + 1 ))
done
