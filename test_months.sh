#!/bin/bash

# Utility script to test every Xth nightly since 2010
step="$1"
skip="$2"
[ ! -z "$step" ] || step=1
[ ! -z "$skip" ] || skip=0

set -e

>test_months.err

month=1
year=2011
while [ $month -le 12 ]; do
  day=1
  while [ $day -le 31 ]; do
    # Break if this month doesn't have this many days (feb: this year)
    date --date="$month/$day $year" &>/dev/null || break
    
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