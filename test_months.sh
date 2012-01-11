#!/bin/bash

# Utility script to test every Xth nightly since 2010
step="$1"

[ ! -z "$step" ] || step=1

set -e

>test_months.err

skip=0
for year in 2010 2011; do
  month=1
  while [ $month -le 12 ]; do
    day=1
    while [ $day -le 31 ]; do
      # Break if this month doesn't have this many days (feb: this year)
      date --date="$month/$day $year" &>/dev/null || break
      
      if [ "$skip" -eq 0 ]; then
        skip=$(( $step - 1 ))
        
        [ $day -ge 10 ] && nday=$day || nday="0$day"
        [ $month -ge 10 ] && nmonth=$month || nmonth="0$month"
        
        # Use getnightly.py to find this build on ftp.mozilla.org
        ret=$(./getnightly.py "$year-$nmonth-$nday" 2>test_months.tmp || true)
        if [ -z "$ret" ]; then
          cat test_months.tmp >> test_months.err
          echo "!! $month/$day/$year -- No build, see test_months.err" | tee -a test_months.log
          day=$(( $day + 1 )) && continue
        fi

        read -ar reta <<< $ret
        timestamp=${reta[0]}
        rev=${reta[1]}
        url=${reta[2]}
        echo ":: $month/$day/$year -- Building: $timestamp, $rev" | tee -a test_months.log
        
        # Get full commit ID from repo
        fullrev=$(
          cd mozilla-central
          hg pull &>/dev/null
          hg log -r "$rev" --template "{node}" || true
        )
        if [ -z "$fullrev" ]; then
          echo "!! Couldn't lookup commit info for nightly build $rev" | tee -a test_months.log
          day=$(( $day + 1 )) && continue
        fi
        
        # Download and extract build
        rm -rf firefox
        echo ":: Downloading build..."
        if ! (curl -# "$url" | tar xj) || [ ! -d "firefox" ]; then
          echo "!! Failed to download build from '$url'" | tee -a test_months.log
          day=$(( $day + 1 )) && continue
        fi
        
        # Run test
        if ! ./slimtest_linux.sh --logfile "logs/$(date +%Y%m%d_%H%M%S)_$commit.log" \
                                 --binary firefox/firefox
                                 --buildname "$rev" \
                                 --buildtime "$timestamp" \
                                 --sqlitedb slimtest.sqlite"$rev" "$timestamp"; then
          echo "!! Build failed, see benchtester log for $rev" | tee -a test_months.log
        fi
      else
        skip=$(( $skip - 1 ))
        day=$(( $day + 1 ))
      fi
    done
    # Increment month
    month=$(( $month + 1 ))
  done
done