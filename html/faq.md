# AWSY FAQ

## What is this site?

''Are We Slim Yet?'' is brought to you by Mozilla's [MemShrink][] team.  We're tasked with monitoring and reducing Firefox's memory usage.

Source for ''Are We Slim Yet?'' and its benchmarks is available on [Github][awsy-github].

## Exactly which versions of Firefox are plotted here?

Every day, Mozilla's build infrastructure generates a new ''nightly build'' of Firefox.  We test the 64-bit Linux nightly builds.

The dates on the x-axis indicate when we switched development ''to'' a given version.  For example, we started developing Firefox 5 on March 3, 2011, but we didn't release it for three months after that.  In the meantime, we started on the code which would become Firefox 6 on April 12.

The memory usage of version that we shipped as "Firefox X" corresponds roughly to the dots under the "FF X+1" line, but we normally make some changes to Firefox X even after we started working on Firefox X+1, and those changes aren't plotted here.

## How is this data generated?

We run a nightly build of Firefox through a benchmark script (written using [mozmill][]) and measure its memory usage at a variety of points along the way.  The testing procedure is as follows.

  * Start the browser, record '''Fresh start''' memory.
  * Run Mozilla's [TP5][] pageload benchmark 5 times.  TP5 loads 100 popular webpages, served from a local webserver.  We load the pages into 30 different tabs (XXX round-robin?), with a XXXs delay between pageloads.
  * Record '''After TP5''' memory usage.  '''After TP5 [+30s, forced GC]''' is measured after sitting idle for 30 seconds and then forcing a garbage collection.
  * Close all open tabs and record '''After TP5, tabs closed''' memory usage.

Every time we measure memory usage, we also collect a full snapshot of about:memory.  You can browse these snapshots by clicking on a point in the graph.

## What's the difference between "resident memory" and "explicit"?

'''Resident memory''' (also known as "resident set size" or RSS) is the single best measure of a process's memory usage.  RSS measures the amount of physical memory (RAM) Firefox's process is using.  This counts code, but does not count memory paged out to disk.

'''Explicit memory''' is memory that Firefox has explicitly allocated, either via `malloc` or `mmap`.  The explicit measure is particularly useful when checking for memory leaks.  If the measured explicit value at two points in time is the same, then we've `free`'d as much as we've `malloc`'ed between those two points in time.  In contrast, the RSS values at those two points might not be the same, for example because our heap might become fragmented.

## "RSS: After TP5, tabs closed [+30s]" is almost twice as high as "RSS: Fresh start" -- doesn't that mean Firefox leaks a ton of memory?

Well, not exactly.

If you look at the equivalent ''explicit'' numbers, you'll see that the "after TP5, tabs closed [+30s]" measure is very close to the "fresh start" measure.  This means Firefox is calling `free()` on almost all the memory it allocated, so it's not leaking memory, at least not in the traditional sense.

So if Firefox has freed all the memory it allocated during the test, why is it using more memory after the test?  Our data shows that most of the difference is due to ''heap fragmentation''.  Before the test, all the objects on our heap are tightly packed.  But after the test, our heap uses twice as much space for the same amount of storage, because the objects on the heap now have gaps between them.

We're [actively exploring][match-startup-mem] ways to minimize heap fragmentation, by [using a new version of our heap allocator][jemalloc2] and trying to minimize the number of calls we make to `malloc`.

Our shows that the peak memory usage after the first run of TP5 is the same as our peak memory usage after the last run of TP5.  This means that, although Firefox remembers how much memory it used at its peak, its memory usage shouldn't increase over time.

## This is all well and good, but my Firefox still leaks like a sive.

We're sorry to hear that, and we'd like to help.  Here are some diagnostic steps you can try.

First, double-check that you're on the latest version of Firefox.  We won't be able to help much if you're running an old version.  You can check for updates in the "Help -> About Firefox" menu.

### Check for add-on leaks

In our experience, most severe leaks in Firefox these days are caused by leaky add-ons.  We know how important add-ons are to our users, and Mozilla's add-ons team has been doing heroic work to find and address leaks in add-ons before our users are affected.  But this work is still in its infancy, and there are a lot of add-ons we haven't yet tested.

To see if add-ons are causing your problems, try [restarting Firefox in safe mode][safe mode], and see if Firefox still leaks.  If safe mode solves your problem, congratulations!  You probably have a leaky add-on.  Now you probably want to know which one is to blame.

To figure out which add-on is leaking, start Firefox up outside safe mode, disable half your add-ons, and see if Firefox still leaks.  Repeat this process to narrow down to just one (or a few) leaky add-ons.  (If it takes a long time for the leak to become aparent, you can look for [zombie compartments][], a common type of leak which is easy to identify even before Firefox starts using gigabytes of memory.)

Once you've figured out which add-on(s) is (are) leaking, you're almost done!  Just [file a bug][], and put "[MemShrink]" in the whiteboard (don't worry about the other metadata like the component; we'll fix it).  We'll contact the add-on developer and help him or her fix the problem.

If you have trouble with any of this, find us on IRC (irc.mozilla.org, #memshrink).  We're happy to help.

### If Firefox still leaks, even in safe mode, file a bug!

If the latest version of Firefox leaks for you, even in safe mode, we definitely want to hear about it.  Please, please [file a bug][], find us on IRC (irc.mozilla.org, #memshrink), send smoke signals...do something!  We need your help, particularly in this case.

[awsy-github]: https://github.com/Nephyrin/MozAreWeSlimYet
[MemShrink]: https://wiki.mozilla.org/Performance/MemShrink
[TP5]: https://wiki.mozilla.org/Buildbot/Talos#tp5
[mozmill]: https://github.com/mozautomation/mozmill
[match-startup-mem]: https://bugzilla.mozilla.org/show_bug.cgi?id=668809
[jemalloc2]: https://bugzilla.mozilla.org/show_bug.cgi?id=580408
[safe mode]: http://support.mozilla.org/en-US/kb/Safe%20Mode
[zombie compartments]: https://developer.mozilla.org/en/Zombie_compartments#Reactive_checking
[file a bug]: https://bugzilla.mozilla.org/enter_bug.cgi?product=Core
