#!/bin/bash

# Utility script to test every Xth nightly since 2010
step="$1"

[ ! -z "$step" ] || step=1

set -e

>test_months.err

skip=0
for year in 2010 2011; do
  month=3
  while [ $month -le 12 ]; do
    day=1
    while [ $day -le 31 ]; do
      # Break if this month doesn't have this many days (feb: this year)
      date --date="$month/$day $year" &>/dev/null || break
      
      if [ "$skip" -eq 0 ]; then
        skip=$(( $step - 1 ))
        
        [ $day -ge 10 ] && nday=$day || nday="0$day"
        [ $month -ge 10 ] && nmonth=$month || nmonth="0$month"
        
        ret=$(./getnightly.py "$year-$nmonth-$nday" 2>test_months.tmp || true)
        if [ ! -z "$ret" ]; then
          unset timestamp rev
          while read line; do
            [ -z "$timestamp" ] && timestamp="$line" || rev="$line"
          done <<< "$ret"
          echo ":: $month/$day/$year -- Building: $timestamp, $rev" | tee -a test_months.log
          if ! ./slimtest_linux.sh "$rev" "$timestamp"; then
            echo "!! Build failed, see benchtester log for $rev"
          fi
        else
          cat test_months.tmp >> test_months.err
          echo "!! $month/$day/$year -- No build, see test_months.err" | tee -a test_months.log
        fi
      else
        skip=$(( $skip - 1 ))
      fi
      # Increment day
      day=$(( $day + 1 ))
    done
    # Increment month
    month=$(( $month + 1 ))
  done
done