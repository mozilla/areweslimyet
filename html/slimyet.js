/* -*- fill-column: 80; js-indent-level: 2; -*- */
/*
 * Copyright © 2012 Mozilla Corporation
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/.
 */

"use strict";

// Vars from query or hash in form #key[:val],...
var gQueryVars = (function () {
  var ret = {};
  function expand(target, outer, inner) {
    var vars = target.split(outer);
    for (var x in vars) {
      x = vars[x].split(inner);
      ret[decodeURIComponent(x[0]).toLowerCase()] = x.length > 1 ? decodeURIComponent(x[1]) : true;
    }
  }
  if (document.location.search)
    expand(document.location.search.slice(1), '&', '=')
  if (document.location.hash)
    expand(document.location.hash.slice(1), ',', ':')
  return ret;
})();

// /mobile/ is an alias for ?mobile
(function () {
  if (document.location.pathname.indexOf('/mobile') == 0)
    gQueryVars['mobile'] = true;

  // Set proper link to inactive
  var inactive = gQueryVars['mobile'] ? '/mobile/' : '/';
  $(function () {
    inactive = $("#navbar a[href='"+inactive+"']");
    inactive.replaceWith($('<span>').addClass('inactive').text(inactive.text()));
  });
})();

/*
 * Annotations to draw on the graph. Format:
 * {
 *   // Anything Date.parse recognizes *or* numeric unix timestamp
 *   'date': "Feb 1 2012 GMT",
 *   // HTML content of tooltip message
 *   'msg': '
 *     We fixed something to do with images sometime before \
 *     <a href="https://hg.mozilla.org/integration/mozilla-inbound/rev/3fdc1c14a8ce">3fdc1c14a8ce</a> \
 *     <p style="color:grey">This is grey text</p> \
 *     <p class="small">yay</p> \
 *   ',
 *   // Optional, disable on desktop or mobile:
 *   'desktop': false,
 *   'mobile': false,
 *   // Show only on some graphs (default all):
 *   'whitelist': [ "Explicit Memory", "Resident Memory" ]
 * }
 */

var gAnnotations = (function() {
  function annoFormat(msg, bugnum) {
    if (bugnum)
      msg += "<br><small>bug " + bugnum + "</small>";
    // Twelve digit lowercase hex -> rev link
    msg = msg.replace(/(\b)([a-f0-9]{12})(\b)/g,
                      '$1<a href="https://hg.mozilla.org/integration/mozilla-inbound/rev/$2">' +
                      '$2</a>$3');
    // Bug 12345 -> Bug link
    msg = msg.replace(/[bB]ug ([0-9]+)/g,
                      '<a href="https://bugzilla.mozilla.org/show_bug.cgi?id=$1">' +
                      '$&</a>');
    return msg;
  }
  var annotations = [
    {
      'date': 1364362111,
      'mobile': false,
      'msg': annoFormat('Decommitted memory is now excluded from explicit',
                        831588),
      // No effect on resident
      'whitelist': [ "Explicit Memory", "Miscellaneous Measurements" ]
    },
    {
      'date': 'Thu May 30 18:33:47 2013 -0700',
      'msg': annoFormat('Images layerization change caused ~40MB regression',
                        867770),
    },
    {
      'date': 'Mon Jun 03 07:57:31 2013 -0700',
      'msg': annoFormat('Image layerization regression fixed', 878062),
    },
    {
      'date': 'Mon Jul 29 17:08:01 2013 GMT',
      'msg': annoFormat('Added heap overhead to explicit; this increased ' +
                        'explicit without increasing our memory usage.', 898558)
    },
    // *************************** Desktop Annotations ***************************
    {
      'date': 1363993909,
      'mobile': false,
      'msg': annoFormat('Multithreaded image decoding leak fixed', 853390)
    },
    {
      'date': 1363788676,
      'mobile': false,
      'msg': annoFormat('Multithreaded image decoding caused us ' +
                        'to leak some documents', 716140)
    },
    {
      'date': 'Jan 28 2013 GMT',
      'mobile': false,
      'msg': annoFormat('15-20 MiB regression in the after-test lines, ' +
                        'likely caused by bug 820602.', 842756)
    },
    {
      'date': 'Fri, 07 Dec 2012 GMT',
      'mobile': false,
      'msg': annoFormat('New HTMLElement bindings caused ~20MB regression ' +
                        'in peak memory consumption', 833518)
    },
    {
      'date': 'Tue, 18 Dec 2012 04:34:31 GMT',
      'mobile': false,
      'msg': annoFormat('~40MB regression (~11%) due to leaked windows.', 820602)
    },
    // *************************** Mobile Annotations ****************************
    {
      'date': 1357139813,
      'desktop': false,
      'msg': annoFormat('Updated android NDK from r5c to r8c.', 828650)
    },
    {
      'date': 1357743011,
      'desktop': false,
      'msg': annoFormat('Some crypto stuff is now being loaded on startup.',
                        824023)
    },
    {
      'date': 1358920410,
      'desktop': false,
      'msg': annoFormat('Some graphics code is loaded earlier, moving the ' +
                        'Start memory usage up but leaving StartSettled as-is.',
                        828126)
    },
    {
      'date': 1358593871,
      'desktop': false,
      'msg': annoFormat('Regression from adding new fonts. Tradeoff ' +
                        'accepted for increased readability. Some of this ' +
                        'was later reduced in bug 844669.', 831354)
    },
    {
      'date': 1359474609,
      'desktop': false,
      'msg': annoFormat('Regression from OS.File debug code, backed out in ' +
                        '8728de36d4a8.', 828201)
    },
    {
      'date': 1361788819,
      'desktop': false,
      'msg': annoFormat('Regression from graphite font shaping, tracked in ' +
                        'bug 846832 and corrected in 6a0bcaa622f0.', 700023)
    },
    {
      'date': 1361831517,
      'desktop': false,
      'msg': annoFormat('Giant drop-spike is a result of the low-memory ' +
                        '<a href="https://staktrace.com/spout/entry.php?id=782">'+
                        'tab zombification</a> behaviour.')
    },
    {
      'date': 1361917561,
      'desktop': false,
      'msg': annoFormat('Giant drop-spike is a result of the low-memory ' +
                        '<a href="https://staktrace.com/spout/entry.php?id=782">'+
                        'tab zombification</a> behaviour.')
    },
    {
      'date': 1361918975,
      'desktop': false,
      'msg': annoFormat('Switched device running the test to a Galaxy Nexus; ' +
                        'baseline values expected to change.')
    },
    {
      'date': 1362421422,
      'desktop': false,
      'msg': annoFormat('Improvement from turning off graphite in fonts.', 846832)
    },
    {
      'date': 1362416958,
      'desktop': false,
      'msg': annoFormat('Improvement from analysis of font-related memory usage.',
                        844669)
    },
    {
      'date': 1363491479,
      'desktop': false,
      'msg': annoFormat('Improvement from zones landing', 759585)
    },
    {
      'date': 1364566105,
      'desktop': false,
      'msg': annoFormat('Regression from Push service landing. Tracked in bug ' +
                        '857135 and corrected in fc8267682725.', 822712)
    },
    {
      'date': 1364841472,
      'desktop': false,
      'msg': annoFormat('Regression being tracked in bug 862390.')
    },
    {
      'date': 1365454665,
      'desktop': false,
      'msg': annoFormat('Improvement from removing push-related components from ' +
                        'Android build.', 857135)
    },
    {
      'date': 1364908990,
      'desktop': false,
      'msg': annoFormat('Small regression from turning on IonMonkey for ARMv6 ' +
                        'Android builds.', 855839)
    },
    {
      'date': 1365004235,
      'desktop': false,
      'msg': annoFormat('Small regression (resident-only) from baseline compiler ' +
                        'landing and making libxul bigger.')
    },
    {
      'date': 1366048480,
      'desktop': false,
      'msg': annoFormat('Regression being tracked in bug 862403.')
    },
    {
      'date': 1369031534,
      'desktop': false,
      'msg': annoFormat('On-demand decompression causes us to double-count things. ' +
                        'The regression here is not actually a regression.', 848764)
    },
    {
      'date': 1369763440,
      'desktop': false,
      'msg': annoFormat('Enabling 24-bit colour on Android causes a memory regression. ' +
                        'It was backed out in 495b385ae811 for test failures.', 803299)
    },
    {
      'date': 1369838059,
      'desktop': false,
      'msg': annoFormat('Enabling 24-bit colour on Android causes a memory regression. ' +
                        'It was backed out in 281dc9793a73 for Tch and Tpan regressions.', 803299)
    },
    {
      'date': 1372195899,
      'desktop': false,
      'msg': annoFormat('Fonts are now loaded directly from the omnijar and decompressed ' +
                        'in memory. This has an acceptable non-startup memory regression.', 878674)
    },
    {
      'date': 1373588395,
      'desktop': false,
      'msg': annoFormat('Elfhack enabled, memory gained.', 892355)
    },
    {
      'date': 1374146101,
      'desktop': false,
      'msg': annoFormat('Elfhack disabled, memory lost.', 894885)
    },
    {
      'date': 1374669205,
      'desktop': false,
      'msg': annoFormat('Elfhack re-enabled, memory re-gained.', 894885)
    },
    {
      'date': 1374806525,
      'desktop': false,
      'msg': annoFormat('Static initializers added in bug 894448, fixed in bug 899368', 899134)
    },
    {
      'date': 1375117971,
      'desktop': false,
      'msg': annoFormat('Increase in GC heap memory, marked WONTFIX', 899584)
    },
    {
      'date': 1375142305,
      'desktop': false,
      'msg': annoFormat('Static initializer fixup', 899368)
    },
    {
      'date': 1376300292,
      'desktop': false,
      'msg': annoFormat('Addon manager change', 906747)
    },
    {
      'date': 1377312199,
      'desktop': false,
      'msg': annoFormat('More static constructors added', 909338)
    },
    {
      'date': 1377545370,
      'desktop': false,
      'msg': annoFormat('Static constructors removed', 909328)
    },
    {
      'date': 1377877508,
      'desktop': false,
      'msg': annoFormat('Updated Fennec profile used in AWSY harness')
    }
  ];

  // Turn dates into date objects, sort by date
  for (var i = 0; i < annotations.length; i++) {
    var anno = annotations[i];
    var date = new Date(typeof(anno['date']) == "number"
                        ? anno['date'] * 1000
                        : anno['date']);
    anno['date'] = date;
  }
  annotations.sort(function(a, b) {
    a = a['date'].getTime();
    b = b['date'].getTime();
    return (a < b) ? -1 : (a == b) ? 0 : 1;
  });
  return annotations;
})();

// Width in pixels of highlight (zoom) selector
var gHighlightWidth = gQueryVars['zoomwidth'] ? +gQueryVars['zoomwidth'] : 400;

// Offset between tooltip and cursor
var gTooltipOffset = 'tooltipoffset' in gQueryVars ? +gQueryVars['tooltipoffset'] : 10;

// Coalesce datapoints to keep them under this many per zoom level.
// Default to 150, or 0 (disabled) if nocondense is supplied
var gMaxPoints = gQueryVars['maxpoints'] ? +gQueryVars['maxpoints'] : (gQueryVars['nocondense'] ? 0 : 150);

// How much time between successfully tested builds on the graph should result
// in a disjointed line. Default 24h
var gDisjointTime = 'disjointtime' in gQueryVars ? +gQueryVars['disjointtime'] : (60 * 60 * 24);

// Merge tooltips if their position is within this many pixels
var gAnnoMergeDist = 'annotationmerge' in gQueryVars ? +gQueryVars['annotationmerge'] : 50;

// 10-class paired qualitative color scheme from http://colorbrewer2.org/.
// Ordered so that the important memory lines are given more prominent colors.
var gDefaultColors = [
  "#A6CEE3", /* light blue */
  "#B2DF8A", /* light green */
  "#FB9A99", /* light red */
  "#FDBF6F", /* light orange */
  "#33A02C", /* dark green */
  "#1F78B4", /* dark blue */
  "#E31A1C", /* dark red */
  "#6A3D9A", /* dark purple */
  "#FF7F00", /* dark orange */
  "#CAB2D6", /* light purple */
];

var gDarkColorsFirst = [
  "#1F78B4", /* dark blue */
  "#33A02C", /* dark green */
  "#E31A1C", /* dark red */
  "#6A3D9A", /* dark purple */
  "#FF7F00", /* dark orange */
  "#A6CEE3", /* light blue */
  "#B2DF8A", /* light green */
  "#FB9A99", /* light red */
  "#CAB2D6", /* light purple */
  "#FDBF6F", /* light orange */
];

// Dates mozilla-central *branched* to form various release trees. Used to
// determine date placement on the X-axis of graphs
// See: https://wiki.mozilla.org/RapidRelease/Calendar
var gReleases = [
  {dateStr: "2011-03-03", name: "FF 4"},
  {dateStr: "2011-04-12", name: "FF 5"},
  {dateStr: "2011-05-24", name: "FF 6"},
  {dateStr: "2011-07-05", name: "FF 7"},
  {dateStr: "2011-08-16", name: "FF 8"},
  {dateStr: "2011-09-27", name: "FF 9"},
  {dateStr: "2011-11-08", name: "FF 10"},
  {dateStr: "2011-12-20", name: "FF 11"},
  {dateStr: "2012-01-31", name: "FF 12"},
  {dateStr: "2012-03-13", name: "FF 13"},
  {dateStr: "2012-04-24", name: "FF 14"},
  {dateStr: "2012-06-05", name: "FF 15"},
  {dateStr: "2012-07-16", name: "FF 16"},
  {dateStr: "2012-08-27", name: "FF 17"},
  {dateStr: "2012-10-08", name: "FF 18"},
  {dateStr: "2012-11-19", name: "FF 19"},
  {dateStr: "2013-01-07", name: "FF 20"},
  {dateStr: "2013-02-18", name: "FF 21"},
  {dateStr: "2013-04-01", name: "FF 22"},
  {dateStr: "2013-05-13", name: "FF 23"},
  {dateStr: "2013-06-24", name: "FF 24"}
];

// Create gReleases[x].date objects
(function() {
  for (var i = 0; i < gReleases.length; i++) {
    // Seconds from epoch.
    gReleases[i].date = Date.parse(gReleases[i].dateStr) / 1000;
  }
})();

// Lookup gReleases by date
var gReleaseLookup = function() {
  var lookup = {};
  for (var i = 0; i < gReleases.length; i++) {
    lookup[gReleases[i].date] = gReleases[i].name;
  }
  return lookup;
}();

// Which series from series.json to graph where with what label. See
// /data/areweslimyet.json and comments below. These are exported from the full
// test database by create_graph_json.py
var gSeries = {
  "Resident Memory" : {
    'StartMemoryResidentV2':         "RSS: Fresh start",
    'StartMemoryResidentSettledV2':  "RSS: Fresh start [+30s]",
    'MaxMemoryResidentV2':           "RSS: After TP5",
    'MaxMemoryResidentSettledV2':    "RSS: After TP5 [+30s]",
    'MaxMemoryResidentForceGCV2':    "RSS: After TP5 [+30s, forced GC]",
    'EndMemoryResidentV2':           "RSS: After TP5, tabs closed",
    'EndMemoryResidentSettledV2':    "RSS: After TP5, tabs closed [+30s]",
    'EndMemoryResidentForceGCV2':    "RSS: After TP5, tabs closed [+30s, forced GC]"
  },
  "Explicit Memory" : {
    'StartMemoryV2':         "Explicit: Fresh start",
    'StartMemorySettledV2':  "Explicit: Fresh start [+30s]",
    'MaxMemoryV2':           "Explicit: After TP5",
    'MaxMemorySettledV2':    "Explicit: After TP5 [+30s]",
    'MaxMemoryForceGCV2':    "Explicit: After TP5 [+30s, forced GC]",
    'EndMemoryV2':           "Explicit: After TP5, tabs closed",
    'EndMemorySettledV2':    "Explicit: After TP5, tabs closed [+30s]",
    'EndMemoryForceGCV2':    "Explicit: After TP5, tabs closed [+30s, forced GC]"
  },
  "Miscellaneous Measurements" : {
    'MaxHeapUnclassifiedV2':  "Heap Unclassified: After TP5 [+30s]",
    'MaxJSV2':                "JS: After TP5 [+30s]",
    'MaxImagesV2':            "Images: After TP5 [+30s]"
  }
};

var gHgBaseUrl = 'https://hg.mozilla.org/integration/mozilla-inbound';

// Select android data. Use the same gSeries, but s/After TP5/After tabs/ and
// prepend 'Android' to series names.
if (gQueryVars['mobile']) {
  for (var series in gSeries) {
    for (var dp in gSeries[series]) {
      gSeries[series]['Android'+dp] = gSeries[series][dp].replace("After TP5", "After tabs");
      delete gSeries[series][dp];
    }
  }
}

// gGraphData pulls /data/<series>.json which has a *condensed* series of builds
// and associated data-lines. After a certain zoom level we need to pull in the
// full-resolution data into gFullData. gGraphData['allseries'] contains info on
// the sub-series that can be fetched for gFullData.
//
// The pre-condensed datapoints and ones we fetch ourselves all have
// min/median/max data, and the revision-range and time-range. See the
// /data/areweslimyet.json file.
//
// _getInvolvedSeries() - Determines if our zoom level justifies using
//   full data series, lists them (none means 'just use gGraphData')
// Plot.SetZoomRange() - Changes the zoom level, if _getInvolvedSeries() advises
//   use of series we don't have, fire off requests for them. Once those have
//   completed, re-render the graph (graph will zoom in, then re-render with
//   more points when they arrive)
//
// Plot._buildSeries() - Builds a series using the logic:
// - *if* we *dont* have gFullData for all ranges involved
//   - Merge every N condensed-points in gGraphData OR
//   - Show all condensed-points in gGraphData [slightly more zoomed]
// - *if* gFullData has the data for all series involved:
//   - Merge those points outselves OR
//   - Show every datapoint (all the way zoomed in)
var gGraphData;
var gFullData = {};

// 'per build data' is /data/<buildname>.json. <buildname> is usually a
// changeset id, but doesn't need to be (although the tooltip assumes they are)
// It primarily contains a dump of the about:memory reporters, and is only used
// for the data-dump you get when clicking on a tooltip. This is fetched/cached
// by getPerBuildData()
var gPerBuildData = {};

// List of *top-level* plots that should be zoom-sync'd
var gZoomSyncPlots = {};

// Range of all non-null datapoints.
var gDataRange;

//
// Utility
//

// Shorthand for $(document.createElement(<e>))[.attr(<attrs>)[.css(<css>)]]
jQuery.new = function(e, attrs, css) {
  var ret = jQuery(document.createElement(e));
  if (attrs) ret.attr(attrs);
  if (css) ret.css(css);
  return ret;
};

// Log message/error to console if available
function logMsg(obj) {
  if (window.console && window.console.log) {
    window.console.log(obj);
  }
}

function logError(obj) {
  if (window.console) {
    if (window.console.error)
      window.console.error(obj)
    else if (window.console.log)
      window.console.log("ERROR: " + obj);
  }
}

// Takes a second-resolution unix timestamp, prints a UTCDate. If the date
// is exactly midnight, remove the "00:00:00 GMT" (we have a lot of timestamps
// condensed to day-resolution)
function prettyDate(aTimestamp) {
  // If the date is exactly midnight, remove the time portion.
  // (overview data is coalesced by day by default)
  return new Date(aTimestamp * 1000).toUTCString().replace('00:00:00 GMT', '');
}

function mkDelta(mem, lastmem) {
  var delta = mem - lastmem;
  var obj = $.new('span').addClass('delta');
  if (delta < 0) {
    obj.text('Δ -'+formatBytes(-delta));
    obj.addClass('neg');
  } else {
    obj.text('Δ '+formatBytes(delta));
    obj.addClass('pos');
  }
  if (Math.abs(delta) / mem > 0.02)
    obj.addClass('significant');
  return obj;
}

function mkHgLink(rev) {
  return $.new('a', { 'class': 'buildlink', 'target': '_blank' })
          .attr('href', gHgBaseUrl + "/rev/" + rev.slice(0,12))
          .text(rev);
}

// float 12039123.439 -> String "12,039,123.44"
// (commas and round %.02)
function prettyFloat(aFloat) {
  var ret = Math.round(aFloat * 100).toString();
  if (ret == "0") return ret;
  if (ret.length < 3)
    ret = (ret.length < 2 ? "00" : "0") + ret;

  var clen = (ret.length - 2) % 3;
  ret = ret.slice(0, clen) + ret.slice(clen, -2).replace(/[0-9]{3}/g, ',$&') + '.' + ret.slice(-2);
  return clen ? ret : ret.slice(1);
}

// Takes a int number of bytes, converts to appropriate units (B/KiB/MiB/GiB),
// returns a prettyFloat()'d string
// formatBytes(923044592344234) -> "859,652.27GiB"
function formatBytes(raw) {
  if (raw / 1024 < 2) {
    return prettyFloat(raw) + "B";
  } else if (raw / Math.pow(1024, 2) < 2) {
    return prettyFloat(raw / 1024) + "KiB";
  } else if (raw / Math.pow(1024, 3) < 2) {
    return prettyFloat(raw / Math.pow(1024, 2)) + "MiB";
  } else {
    return prettyFloat(raw / Math.pow(1024, 3)) + "GiB";
  }
}

// Pass to progress on $.ajax to show the progress div for this request
function dlProgress() {
  var xhr = $.ajaxSettings.xhr();
  var url;
  if (xhr) {
    xhr._open = xhr.open;
    xhr.open = function() {
      if (arguments.length >= 2)
        url = arguments[1];
      return this._open.apply(this, arguments);
    };
    xhr.addEventListener("progress", function(e) {
      // We can't use e.total because it is bogus for gzip'd data: Firefox sets
      // loaded to the decompressed data but total to compressed, and chromium
      // doesn't set total.
      if (e.loaded) {
        if (e.loaded == e.total) {
          $('#dlProgress').empty();
        } else {
          $('#dlProgress').text("Downloading " + url + " - " +
                                formatBytes(e.loaded));
        }
      }
    }, false);
  }
  return xhr;
}

// Round unix timestamp to the nearest midnight UTC. (Not *that day*'s midnight)
function roundDay(date) {
  return Math.round(date / (24 * 60 * 60)) * 24 * 60 * 60;
}

// Round a date (seconds since epoch) up to the next day.
function roundDayUp(date) {
  return Math.ceil(date / (24 * 60 * 60)) * 24 * 60 * 60;
}

// Round a date (seconds since epoch) down to the previous day.
function roundDayDown(date) {
  return Math.floor(date / (24 * 60 * 60)) * 24 * 60 * 60;
}

// Get the full time range covered by two (possibly condensed) build_info structs
function getBuildTimeRange(firstbuild, lastbuild)
{
  var range = [];
  if ('timerange' in firstbuild && firstbuild['timerange'][0] < firstbuild['time'])
    range.push(firstbuild['timerange'][0]);
  else
    range.push(firstbuild['time']);

  if ('timerange' in lastbuild && lastbuild['timerange'][1] > lastbuild['time'])
    range.push(lastbuild['timerange'][1]);
  else
    range.push(lastbuild['time']);

  return range;
}

//
// For the about:memory-esque display
//

// Expand a tree node
function treeExpandNode(node, noanimate) {
  if (!node.is('.hasChildren')) return;

  var subtree = node.find('.subtree');
  if (!subtree.length) {
    var subtree = $.new('div').addClass('subtree').hide();
    memoryTreeNode(subtree, node.data('nodeData'),
                              node.data('select'),
                              node.data('depth'));
    subtree.appendTo(node);
  }
  if (noanimate)
    subtree.show();
  else
    subtree.slideDown(250);
  node.children('.treeNodeTitle').find('.treeExpandClicker').text('[-]');
}

// Collapse a tree node
function treeCollapseNode(node) {
  node.children('.subtree').slideUp(250);
  node.children('.treeNodeTitle').find('.treeExpandClicker').text('[+]');
}

// Collapse/Expand a tree node
function treeToggleNode(node) {
  if (node.find('.subtree:visible').length)
    treeCollapseNode(node);
  else
    treeExpandNode(node);
}

// Create a about:memory-esque tree of values from a list of nodes.
// The 'datapoint' value is the name of the point to highlight within the tree.
// This is a wrapper for memoryTreeNode()
function makeMemoryTree(title, nodes, datapoint) {
  var memoryTree = $.new('div', { class: 'memoryTree' }, { display: 'none' });
  // memoryTree title
  var treeTitle = $.new('div', { class: 'treeTitle' }).appendTo(memoryTree);
  $.new('h3').text(title)
              .appendTo(treeTitle);
  // datapoint subtitle
  $.new('div').addClass('highlight')
              .text(datapoint.replace(/\//g, ' -> '))
              .appendTo(treeTitle);
  memoryTreeNode(memoryTree, nodes, datapoint);

  return memoryTree;
}

// render a memory tree into <target>, with node data <data>. The node specified
// by <select> should be highlighted. <depth> represents how many levels deep
// this branch is in the overall tree.
function memoryTreeNode(target, data, select, depth) {
  if (depth === undefined)
    depth = 0;

  // TODO Use 'mixed' units as an indicator of container nodes instead of hard
  //      coding.
  var showVal = depth >= 2;
  var showPct = depth >= 3;

  // if select is passed as "a/b/c", split it so it is an array
  if (typeof(select) == "string") {
    select = select.split('/');
  }

  function defval(obj) {
    if (typeof(obj) == 'number')
      return obj
    return obj['_val'] == undefined ? null : obj['_val'];
  }

  // Sort nodes
  var rows = [];
  for (var node in data) {
    // Nodes starting with _ are not children (_val, _sum, _units)
    if (node[0] == '_')
      continue;
    rows.push(node);
  }
  if (showVal) {
    // Sort by memory size
    rows.sort(function (a, b) {
      var av = defval(data[a]) == null ? 0 : defval(data[a]);
      var bv = defval(data[b]) == null ? 0 : defval(data[b]);
      return bv - av;
    });
  } else {
    // Sort reverse alphanumeric
    rows = rows.sort(function (a, b) { return a == b ? 0 : a < b ? 1 : -1 });
  }

  // Add rows
  var parentval = defval(data);
  var node;
  while (node = rows.shift()) {
    var leaf = true;
    if (typeof(data[node]) != 'number') {
      for (var key in data[node])
        if (key[0] !== '_')
          leaf = false
    }
    var treeNode = $.new('div')
                    .addClass('treeNode')
                    .data('nodeData', data[node])
                    .data('depth', depth + 1);
    var nodeTitle = $.new('div')
                     .addClass('treeNodeTitle')
                     .appendTo(treeNode);

    // Add value if inside a memNode
    var val = defval(data[node]);
    if (showVal && val != null) {
      // Value
      var prettyval;
      if (data[node] instanceof Object && '_units' in data[node]) {
        if (data[node]['_units'] == 'pct')
          // 'percent' memory reporters are fixed point
          prettyval = (val / 100).toFixed(2) + '%';
        else if (data[node]['_units'] == 'cnt')
          // 'count' memory reporters are unitless
          prettyval = val
        else
          logError("unknown unit type " + data[node]['_units']);
      } else {
        // Default unit is bytes
        prettyval = formatBytes(val);
      }
      $.new('span').addClass('treeValue')
                   .text(prettyval)
                   .appendTo(nodeTitle);
      // Percentage of parent node
      var pct = "("+prettyFloat(100* (val / parentval))+"%)";
      if (showPct && parentval != null) {
        $.new('span').addClass('treeValuePct')
                     .text(pct)
                     .appendTo(nodeTitle);
      }
    }

    // Add label
    var title = node;
    var subtitle;
    if (subtitle = /^(.+)\((.+)\)$/.exec(node)) {
      title = subtitle[1];
      subtitle = subtitle[2];
    }
    var label = $.new('span').addClass('treeNodeLabel')
                             .appendTo(nodeTitle).text(title);
    if (subtitle) {
      $.new('span').addClass('subtitle').text(' '+subtitle).appendTo(label);
    }

    // Add treeExpandClicker and click handler if node has children
    var expandClick = $.new('span').addClass('treeExpandClicker');
    nodeTitle.prepend(expandClick);
    if (!leaf) {
      expandClick.text('[+]');
      nodeTitle.click(function () { treeToggleNode($(this).parent()); });
      treeNode.addClass('hasChildren');
    }

    // Handle selecting a start node
    if (select && node == select[0]) {
      if (select.length == 1) {
        treeNode.addClass('highlight');
      } else {
        treeNode.data('select', select.splice(1));
      }
      treeExpandNode(treeNode, true);
    }

    target.append(treeNode);
  }
}

// If this range is 'zoomed' enough to warrant using full-resolution data
// (based on gMaxPoints), return the list of gFullData series names that would
// be needed. Return false if overview data is sufficient for this range.
// It's up to the caller to call getFullSeries(name) to start downloading any
// of these that arn't downloaded.
function _getInvolvedSeries(range) {
  var ret = [];
  var groupdist = Math.round((range[1] - range[0]) / gMaxPoints);

  // Unless the requested grouping distance is < 80% of the overview data's
  // distance, don't pull in more
  if (!gQueryVars['nocondense'] && isFinite(groupdist) &&
      groupdist / gGraphData['condensed'] > 0.8)
    return null;

  for (var x in gGraphData['allseries']) {
    var s = gGraphData['allseries'][x];
    if (range[1] >= s['fromtime'] && range[0] <= s['totime'])
      ret.push(s['dataname']);
  }

  return ret;
}

// Helper to call _getInvolvedSeries and call GetFullSeries on all results, with
// final callback.
function _fetchInvolvedSeries(range, callback) {
  var fullseries = _getInvolvedSeries(range);
  var queued = 0;
  var pending = 0;
  for (var x in fullseries) {
    if (!(fullseries[x] in gFullData)) {
      pending++;
      var self = this;
      getFullSeries(fullseries[x], function () {
        if (--pending == 0)
          callback.call(null, queued);
      });
    }
  }
  queued = pending;
  if (queued == 0)
    callback.call(null, 0);
}

//
// Tooltip
//

// A tooltip that can be positioned relative to its parent via .hover(),
// or 'zoomed' to inflate and cover its parent via .zoom()
function Tooltip(parent) {
  if ((!this instanceof Tooltip)) {
    logError("Tooltip() used incorrectly");
    return;
  }
  this.obj = $.new('div', { 'class' : 'tooltip' }, { 'display' : 'none' });
  this.content = $.new('div', { 'class' : 'content' }).appendTo(this.obj);
  if (parent)
    this.obj.appendTo(parent);

  // Track mouseover state for delayed fade out
  var self = this;
  this.mouseover = false;
  this.obj.bind("mouseover", function(e) {
    self.mouseover = true;
    self._fadeIn();
  });
  this.obj.mouseleave(function(e) {
    self.mouseover = false;
    if (self.obj.is(":visible") && !self.hovered && !self.isZoomed()) {
      self._fadeOut();
    }
  });

  this.obj.data('owner', this);
  this.hovered = false;
  this.onUnzoomFuncs = [];
  this.faded = true;
}

Tooltip.prototype.isZoomed = function () { return this.obj.is('.zoomed'); }

Tooltip.prototype.append = function(obj) {
  this.content.append(obj);
}

Tooltip.prototype.empty = function() {
  this.content.empty();
  this.seriesname = null;
  this.buildset = null;
  this.buildindex = null;
}

Tooltip.prototype.hover = function(x, y, nofade) {
  if (this.isZoomed())
    return;

  this.hovered = true;
  var poffset = this.obj.parent().offset();

  var h = this.obj.outerHeight();
  var w = this.obj.outerWidth();
  // Lower-right of cursor
  var top = y + gTooltipOffset;
  var left = x + gTooltipOffset;
  // Move above cursor if too far down
  if (window.innerHeight + window.scrollY < poffset.top + top + h + 30)
    top = y - h - gTooltipOffset;
  // Move left of cursor if too far right
  if (window.innerWidth + window.scrollX < poffset.left + left + w + 30)
    left = x - w - gTooltipOffset;

  this.obj.css({
    top: top,
    left: left
  });

  // Show tooltip
  if (!nofade)
    this._fadeIn();
}

Tooltip.prototype.unHover = function() {
  if (this.isZoomed())
    return;
  this.hovered = false;
  if (!this.mouseover) {
    // Don't actually fade till the mouse goes away, see handlers in constructor
    this._fadeOut();
  }
}

Tooltip.prototype._fadeIn = function() {
  if (this.faded) {
    this.obj.stop().fadeTo(200, 1);
    this.faded = false;
  }
}

Tooltip.prototype._fadeOut = function() {
  this.faded = true;
  this.obj.stop().fadeTo(200, 0, function () { $(this).hide(); });
}

// value      - Value of displayed point
// label      - tooltip header/label
// buildset   - set of builds shown for this graph (different from gBuildInfo as
//              it may have been condensed)
// buildindex - index of this build in buildset
// series     - the series we are showing
Tooltip.prototype.showBuild = function(label, series, buildset, buildindex, seriesname) {
  this.empty();
  this.build_series = series;
  this.build_seriesname = seriesname;
  this.build_set = buildset;
  this.build_index = buildindex;

  var value = series[buildindex][1];
  var build = buildset[buildindex];
  var rev = build['firstrev'].slice(0,12);

  // Label
  this.append($.new('h3').text(label));
  // Build link / time
  var ttinner = $.new('p');
  var valobj = $.new('p').text(formatBytes(value) + ' ');
  // Delta
  if (buildindex > 0) {
    valobj.append(mkDelta(value, series[buildindex - 1][1]));
  }
  ttinner.append(valobj);
  ttinner.append($.new('b').text('build '));
  ttinner.append(mkHgLink(rev));
  if (build['lastrev']) {
    // Multiple revisions, add range link
    ttinner.append(' .. ');
    ttinner.append(mkHgLink(build['lastrev'].slice(0,12)));
  }
  if (buildindex > 0) {
    // Add pushlog link
    // Because 'merged' points use median values for the graph data, we
    // show the broadest push log possible when dealing with them
    var prevbuild = buildset[buildindex - 1];
    if (prevbuild && prevbuild['firstrev']) {
      var prevrev = prevbuild['firstrev'].slice(0,12);
      var pushrev = build['lastrev'] ? build['lastrev'].slice(0,12) : rev;
      var pushlog = gHgBaseUrl + "/pushloghtml?fromchange=" + prevrev + "&tochange=" + pushrev;
      ttinner.append(" (");
      ttinner.append($.new('a', { 'href' : pushlog, 'target' : '_blank' })
                     .text("pushlog"));
      ttinner.append(")");
    }
  }
  // Time
  ttinner.append($.new('p').addClass('timestamp').text(prettyDate(build['time'])));
  // Full timerange (shown on zoom)
  if (build['lastrev'] && build['timerange']) {
    var timerange = $.new('p').addClass('timerange').hide();
    timerange.append(prettyDate(build['timerange'][0]));
    timerange.append(' — ');
    timerange.append(prettyDate(build['timerange'][1]));
    ttinner.append(timerange);
  }
  var self = this;
  ttinner.append($.new('p').addClass("hoverNote")
                 .text("click for full memory info").click(function () {
                   self.buildDetail();
                 }));
  this.append(ttinner);
}

// The zoomed build-detail view for builds we represent. Requires the tooltip be
// visible and initialized with showBuild();
Tooltip.prototype.buildDetail = function() {
  this.zoom();

  // We should already be populated from showBuild().
  // Zoom tooltip, remove the 'click to hover' note and add a loading banner.
  var loading = $.new('h2', null, {
    display: 'none',
    'text-align': 'center',
  }).text('Loading test data...').attr('id', 'loading');

  // Switch to showing full timerange until unzoomed
  var timerangeobj = this.content.find('.timerange');
  if (timerangeobj.length) {
    var timeobj = this.content.find('.timestamp');
    timeobj.insertBefore(timerangeobj);
    timeobj.addClass('fading').fadeOut(250);
    timerangeobj.removeClass('fading').fadeIn(250);
    this.onUnzoom(function () {
      timerangeobj.insertBefore(timeobj);
      timerangeobj.addClass('fading').fadeOut(250);
      timeobj.removeClass('fading').fadeIn(250);
    });
  }

  this.append(loading);
  this.obj.find(".hoverNote").remove();
  loading.fadeIn();

  var self = this;
  var build = this.build_set[this.build_index];

  if ('lastrev' in build) {
    // Build is a series. We need to make sure we have full res data to
    // enumerate all the builds in this range.
    this._asyncHelper(_fetchInvolvedSeries, build['timerange'], function() {
      self.append(self._buildlistView());
    });
  } else {
    // Only one build, just display memory view
    var revision = build['firstrev'];
    this._asyncHelper(getPerBuildData, revision, function () {
      var memoryview = self._memoryView(revision);
      self.append(memoryview);
      memoryview.fadeIn(250);
    });
  }
}

// Wraps a |someAsyncThing(arg, success_callback, fail_callback)| style call,
// handling fading in/out the 'Loading...' message, displaying an error, and
// aborting if the tooltip leaves zoom mode.
Tooltip.prototype._asyncHelper = function(target, arg, success) {
  var loading = this.obj.find('#loading');
  var canceled = false;
  this.onUnzoom(function () { canceled = true; });

  var self = this;
  target.call(null, arg, function () {
    // Success
    if (!canceled) {
      loading.addClass('fading').fadeOut(250);
      success.call(null);
    }
  }, function (error) {
    // Failed
    if (!canceled) {
      loading.text("Failed to fetch data :(");
      logError("Error while loading data: " + error);
      self.content.append($.new('p').css({ 'color': 'red', 'text-align': 'center' })
                           .text("Error: " + error));
    }
  });
}

Tooltip.prototype._buildlistView = function () {
  // Get the full list of builds our condensed build covers
  var condensedbuild = this.build_set[this.build_index];
  var involvedseries = _getInvolvedSeries(condensedbuild['timerange']);
  var self = this;
  var loading = this.content.find('#loading');

  var wrapper = $.new('div').addClass('buildList');
  var header = $.new('div').addClass('buildListHead').appendTo(wrapper);
  $.new('div').addClass('buildListSubHead').appendTo(wrapper)
              .text('Only revisions with test data shown, range may include more changesets');
  var obj = $.new('div').addClass('buildListContent').appendTo(wrapper);
  var numbuilds = 0;

  var lastmem;
  var min = null;
  var max = null;
  var first = null;
  var last = null;
  var start;

  for (var m = 0; m < involvedseries.length; m++) {
    var series = gFullData[involvedseries[m]];
    for (var n = 0; n < series.builds.length; n++) {
      var mem = series.series[this.build_seriesname][n];
      var build = series.builds[n];
      // Scan to first build
      if (!start && build['revision'] == condensedbuild['firstrev']) {
        start = true;
      } else if (!start) {
        if (mem !== null) {
          lastmem = mem;
        }
        continue;
      }

      if (mem !== null) {
        if (!first) {
          first = mem;
        }
        numbuilds++;
        //
        // Create build link and append to list
        //
        var buildcrumb = $.new('div', { 'class': 'buildcrumb' });

        // series value for this build
        // [view]
        buildcrumb.append('[');
        var viewlink  = $.new('a', { 'href': '#' })
                         .text('view')
                         .appendTo(buildcrumb);
        buildcrumb.append('] ');
        // revision (also takes you to hg)
        buildcrumb.append(mkHgLink(build['revision']));
        // Memory usage
        buildcrumb.append($.new('span').text(' ' + formatBytes(mem)));
        // delta
        if (lastmem) {
          var deltaobj = mkDelta(mem, lastmem);
          buildcrumb.append(' ');
          buildcrumb.append(deltaobj);
        }

        // track min/max
        if (max === null || mem > max) max = mem;
        if (min === null || mem < min) min = mem;
        lastmem = mem;

        viewlink.click(function (rev) {
          // Close over rev
          return function() {
            if (obj.is('.fading'))
              return;

            // Fade out buildlist, fade in loading, fade in memoryview when fetch
            // completes.
            wrapper.insertBefore(loading);
            wrapper.addClass('fading').fadeOut(250);
            loading.removeClass('fading').fadeIn(250);
            self._asyncHelper(getPerBuildData, rev, function () {
              var memoryview = self._memoryView(rev);
              // Append back arrow to memory view
              var back = $.new('a', { 'href': '#', 'class': 'button backButton' })
                          .text('[<- list]')
                          .click(function () {
                  // Return to buildlist view
                  memoryview.addClass('fading').fadeOut(250, function () {
                    memoryview.remove();
                  });
                  wrapper.removeClass('fading').fadeIn(250);
                  return false;
                });
              memoryview.find('.treeTitle').prepend(back);
              // insertBefore so it get pushed down by the buildlist when the
              // buildlist fades back in. (while the memory view would still be
              // fading out)
              memoryview.insertBefore(wrapper);
              memoryview.fadeIn(250);
            });
            return false;
          };
        } (build['revision']));

        obj.append(buildcrumb);
      }

      // Stop at lastrev
      if (build['revision'] == condensedbuild['lastrev']) {
        last = mem !== null ? mem : lastmem;
        // Break out of nested loop
        m = involvedseries.length;
        break;
      }
    }
  }

  // Fill header now that we counted builds and min/max
  header.append($.new('p').text('Datapoint is the median of ' + numbuilds + ' tests'));
  header.append(mkDelta(last, first));
  header.append($.new('span').addClass('small')
                 .text(' ( ' + formatBytes(min) + ' min, ' + formatBytes(max) + ' max )'));
  return wrapper;
}

Tooltip.prototype._memoryView = function(revision) {
  // Build zoomed tooltip
  var series_info = gGraphData['series_info'][this.build_seriesname];
  var nodes = gPerBuildData[revision][series_info['test']]['nodes'];
  var datapoint = series_info['datapoint'];

  // series_info['datapoint'] might be a list of aliases for the datapoint.
  // find the one actually used in this node tree.
  if (datapoint instanceof Array) {
    for (var i = 0; i < datapoint.length; i++) {
      var dlist = datapoint[i].split('/');
      var p = nodes;
      while (dlist.length) {
        p = p[dlist.shift()];
        if (!p) break;
      }
      if (p) {
        datapoint = datapoint[i];
        break;
      }
    }
  }

  var title = series_info['test'] + ' :: ' + revision.slice(0,12);
  return makeMemoryTree(title, nodes, datapoint);
}

Tooltip.prototype.zoom = function(callback) {
  var w = this.obj.parent().width();
  var h = this.obj.parent().height();

  // If the parent is offscreen, try to bump it on screen if we can
  var offset = this.obj.parent().offset();
  var scrolltop = $('html,body').scrollTop();
  var scroll = scrolltop;

  if (scroll + window.innerHeight < offset.top + h)
    scroll = offset.top - (window.innerHeight - h) + 20;
  if (scroll > offset.top)
    scroll = offset.top - 20;

  if (scroll != scrolltop)
    $('html,body').animate({ 'scrollTop' : scroll }, 500);

  this.obj.show();
  // Animate these by pixel values to workaround wonkiness in jquery+chrome
  this.obj.stop().addClass('zoomed').animate({
    width: Math.round(0.94 * w) + 'px',
    height: Math.round(0.95 * h) + 'px',
    left: Math.round(0.03 * w) + 'px',
    top: '0px',
    opacity: 1
  }, 500, null, callback);

  // Close button
  var self = this;
  $.new('a', { class: 'button closeButton', href: '#' })
   .text('[x]')
   .appendTo(this.obj).css('display', 'none')
   .fadeIn(500).click(function () {
     self.unzoom();
     return false;
   });
}

Tooltip.prototype.onUnzoom = function(callback) {
  if (this.isZoomed())
    this.onUnzoomFuncs.push(callback);
}

Tooltip.prototype.unzoom = function() {
  if (this.isZoomed() && !this.obj.is(':animated'))
  {
    var w = this.obj.parent().width();
    var h = this.obj.parent().height();
    var self = this;
    this.obj.animate({
        width: Math.round(0.5 * w) + 'px',
        height: Math.round(0.5 * h) + 'px',
        top: Math.round(0.25 * h) + 'px',
        left: Math.round(0.25 * w) + 'px',
        opacity: '0'
      }, 250, function() {
        self.obj.removeAttr('style').hide().removeClass('zoomed');
        self.obj.find('.closeButton').remove();
    });

    var callback;
    while (callback = this.onUnzoomFuncs.pop())
      callback.apply(this);
  }
}

//
// Ajax for getting more graph data
//

// Fetch the series given by name (see gGraphData['allseries']), call success
// or fail callback. Can call these immediately if the data is already available
var gPendingFullData = {}
function getFullSeries(dataname, success, fail) {
  if (dataname in gFullData) {
    if (success instanceof Function)
      window.setTimeout(success, 0);
  } else {
    if (!(dataname in gPendingFullData)) {
      gPendingFullData[dataname] = { 'success': [], 'fail': [] };
      $.ajax({
        xhr: dlProgress,
        url: '/data/' + dataname + '.json',
        success: function (data) {
          gFullData[dataname] = data;
          for (var i in gPendingFullData[dataname]['success'])
            gPendingFullData[dataname]['success'][i].call(null);
          delete gPendingFullData[dataname];
        },
        error: function(xhr, status, error) {
          for (var i in gPendingFullData[dataname]['fail'])
            gPendingFullData[dataname]['fail'][i].call(null, error);
          delete gPendingFullData[dataname];
        },
        dataType: 'json'
      });
    }
    if (success) gPendingFullData[dataname]['success'].push(success);
    if (fail) gPendingFullData[dataname]['fail'].push(fail);
  }
}

// Fetch the full memory dump for a build. Calls success() or fail() callbacks
// when the data is ready (which can be before the call even returns)
// (gets /data/<buildname>.json)
function getPerBuildData(buildname, success, fail) {
  if (gPerBuildData[buildname] !== undefined) {
    if (success instanceof Function) success.apply(null);
  } else {
    $.ajax({
      xhr: dlProgress,
      url: '/data/' + buildname + '.json',
      success: function (data) {
        gPerBuildData[buildname] = data;
        if (success instanceof Function) success.call(null);
      },
      error: function(xhr, status, error) {
        if (fail instanceof Function) fail.call(null, error);
      },
      dataType: 'json'
    });
  }
}

//
// Plot functions
//

//
// Creates a plot, appends it to <appendto>
// - axis -> { 'AxisName' : 'Nicename', ... }
//
function Plot(name, appendto) {
  if (!this instanceof Plot) {
    logError("Plot() used incorrectly");
    return;
  }

  this.name = name;
  this.axis = gSeries[name];
  this.zoomed = false;

  this.dataRange = gDataRange;
  logMsg("Generating graph \""+name+"\", data range - " + JSON.stringify(this.dataRange));
  this.zoomRange = this.dataRange;

  this.container = $.new('div').addClass('graphContainer');
  if (appendto) this.container.appendTo(appendto);
  $.new('h2').text(name).appendTo(this.container);
  this.rhsContainer = $.new('div').addClass('rhsContainer').appendTo(this.container);
  this.zoomOutButton = $.new('a', { href: '#', class: 'zoomOutButton' })
                        .appendTo(this.rhsContainer)
                        .text('Zoom Out')
                        .hide()
                        .click(function () {
                          self.setZoomRange();
                          return false;
                        });
  this.legendContainer = $.new('div').addClass('legendContainer').appendTo(this.rhsContainer);

  this.obj = $.new('div').addClass('graph').appendTo(this.container);
  this.flot = $.plot(this.obj,
    // Data
    this._buildSeries(this.zoomRange[0], this.zoomRange[1]),
    // Options
    {
      series: {
        lines: { show: true },
        points: { show: true }
      },
      grid: {
        color: "#aaa",
        hoverable: true,
        clickable: true
      },
      xaxis: {
        ticks: function(axis) {
          var points = [];
          for (var i = 0; i < gReleases.length; i++) {
            var date = gReleases[i].date;
            if (axis.min <= date && date <= axis.max) {
              points.push(date);
            }
          }

          if (points.length >= 2) {
            return points;
          }

          if (points.length == 1) {
            var minDay = roundDayUp(axis.min);
            var maxDay = roundDayDown(axis.max);

            if (Math.abs(points[0] - minDay) > Math.abs(points[0] - maxDay)) {
              points.push(minDay);
            }
            else {
              points.push(maxDay);
            }

            return points;
          }

          points.push(roundDayUp(axis.min));
          points.push(roundDayDown(axis.max));

          return points;
        },

        tickFormatter: function(val, axis) {
          var abbrevMonths = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul',
                              'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
          var date = new Date(val * 1000);

          var releaseName = "";
          if (gReleaseLookup[val]) {
            releaseName = '<div class="tick-release-name">' + gReleaseLookup[val] + '</div>';
          }

          return '<div class="tick-day-month">' + date.getUTCDate() + ' ' +
                 abbrevMonths[date.getUTCMonth()] + '</div>' +
                 '<div class="tick-year">' + date.getUTCFullYear() + '</div>' +
                 releaseName;
        }
      },
      yaxis: {
        ticks: function(axis) {
          // If you zoom in and there are no points to show, axis.max will be
          // very small.  So let's say that we'll always graph at least 32mb.
          var axisMax = Math.max(axis.max, 32 * 1024 * 1024);

          var approxNumTicks = 10;
          var interval = axisMax / approxNumTicks;

          // Round interval up to nearest power of 2.
          interval = Math.pow(2, Math.ceil(Math.log(interval) / Math.log(2)));

          // Round axis.max up to the next interval.
          var max = Math.ceil(axisMax / interval) * interval;

          // Let res be [0, interval, 2 * interval, 3 * interval, ..., max].
          var res = [];
          for (var i = 0; i <= max; i += interval) {
            res.push(i);
          }

          return res;
        },

        tickFormatter: function(val, axis) {
          return val / (1024 * 1024) + ' MiB';
        }
      },
      legend: {
        container: this.legendContainer
      },
      colors: name.indexOf('Memory') != -1 ? gDefaultColors : gDarkColorsFirst
    }
  );

  // If our condensed data is not enough to satisfy gMaxPoints
  // (e.g. ?maxpoints=9000) we'll need to fetch high resolution series and
  // re-render.
  var self = this;
  _fetchInvolvedSeries(this.dataRange, function (fetched) {
    if (fetched > 0)
      self.setZoomRange(self.zoomRange, true);
  });

  //
  // Background selector for zooming
  //
  var fcanvas = this.flot.getCanvas();
  this.zoomSelector = $.new('div', null,
                       {
                         top: this.flot.getPlotOffset().top + 'px',
                         height: this.flot.height() - 10 + 'px', // padding-top is 10px
                       })
                       .addClass('zoomSelector')
                       .text("zoom")
                       .insertBefore(fcanvas);

  // For proper layering
  $(fcanvas).css('position', 'relative');

  //
  // Graph Tooltip
  //

  // Setup annotations container
  var offset = this.flot.getPlotOffset();
  this.annotations = $.new('div').addClass('annotations')
                      .css('width', this.flot.width() + 'px')
                      .css('left', offset.left + 'px')
                      .css('top', offset.top + 'px');
  this.obj.prepend(this.annotations);
  this._drawAnnotations();

  this.tooltip = new Tooltip(this.container);
  var self = this;
  this.obj.bind("plotclick", function(event, pos, item) { self.onClick(item); });
  this.obj.bind("plothover", function(event, pos, item) { self.onHover(item, pos); });
  this.obj.bind("mouseout", function(event) { self.hideHighlight(); });
}

// Zoom this graph to given range. If called with no arguments, zoom all the way
// back out. range is of format [x1, x2]. this.dataRange contains the range of
// all data, this.zoomRange contains currently zoomed range if this.zoomed is
// true.
// If the specified range warrents fetching full data (getFullSeries), but we
// don't have it, issue the ajax and set a callback to re-render the graph when
// it returns (so we'll zoom in, but then re-render moments later with more
// points)
Plot.prototype.setZoomRange = function(range, nosync) {
    var zoomOut = false;
    if (range === undefined)
      range = this.dataRange;
    if (range[0] == this.dataRange[0] && range[1] == this.dataRange[1])
      zoomOut = true;

    var self = this;
    if (this.zoomed && zoomOut) {
      // Zooming back out, remove zoom out button
      this.zoomed = false;
      self.zoomOutButton.hide();
    } else if (!this.zoomed && !zoomOut) {
      // Zoomed out -> zoomed in. Add zoom out button.
      this.zoomed = true;
      self.zoomOutButton.show();
    }

    // If there are sub-series we should pull in that we haven't cached,
    // set requests for them and reprocess the zoom when complete
    _fetchInvolvedSeries(range, function (fetched) {
      if (fetched > 0)
        self.setZoomRange(self.zoomRange, true);
    });

    this.zoomRange = range;
    var newseries = this._buildSeries(range[0], range[1]);
    this.flot.setData(newseries);
    this.flot.setupGrid();
    this.flot.draw();
    this._drawAnnotations();

    // The highlight has the wrong range now that we mucked with the graph
    if (this.highlighted)
      this.showHighlight(this._highlightLoc, this._highlightWidth);

    // Sync all other plots
    if (!nosync)
      for (var x in gZoomSyncPlots)
        if (gZoomSyncPlots[x] != this)
          gZoomSyncPlots[x].setZoomRange(zoomOut ? undefined : range, true);
}

// Takes two timestamps and builds a list of series based on this plot's axis
// suitable for passing to flot - condensed to try to hit gMaxPoints.
// Uses series returned by _getInvolvedSeries *if they are all downloaded*,
// otherwise always uses overview data.
// See comment about gFullData at top of file
Plot.prototype._buildSeries = function(start, stop) {
  var self = this; // for closures
  var involvedseries = _getInvolvedSeries([start, stop]);

  // Don't use the involved series if they're not all downloaded
  for (var x in involvedseries) {
    if (!gFullData[involvedseries[x]]) {
      involvedseries = false;
      break;
    }
  }

  // Push a dummy null point at the beginning of the series to force the zoom to
  // start exactly there

  var builds = [ { time: start, timerange: [ start, start ] } ];
  var data = {};

  for (var axis in this.axis)
    data[axis] = [ [ start, null ] ];

  // Grouping distance
  var groupdist = gMaxPoints == 0 ? 0 : Math.round((stop - start) / gMaxPoints);

  // Points might be [min, median, max], or just a number if it only
  // represents one datapoint.
  function pval(point, ind) {
    var ret = (point instanceof Array) ? point[ind] : point;
    return (ret === null) ? ret : +ret;
  }

  function pushdp(series, buildinf, ctime) {
    // Push a datapoint onto builds/data
    if (ctime != -1) {
      // Flatten the axis first and determine if this is a null build
      var flat = {};
      var nullbuild = true;
      for (var axis in self.axis) {
        flat[axis] = flatten(series[axis]);
        if (flat[axis] !== null)
          nullbuild = false;
      }
      if (nullbuild) {
        // Null builds in the series cause the line to be disjointed. Only push
        // one if there is >= 24h of consecutive untested builds.
        var diff = builds.length ? buildinf['timerange'][0] -
                                   builds[builds.length - 1]['timerange'][1]
                                 : 0;
        if (diff < gDisjointTime)
          return;
      }
      // Add to series
      builds.push(buildinf);
      for (axis in self.axis) {
        data[axis].push([ +buildinf['time'], flat[axis] ]);
      }
    }
  }
  function groupin(timestamp) {
    return groupdist > 0 ? timestamp - (timestamp % groupdist) : timestamp;
  }
  // Given a list of numbers, return [min, median, max]
  function flatten(series) {
    var iseries = [];
    for (var x in series) {
      if (series[x] !== null) {
        if (series[x] instanceof Array) {
          // [ median, count ] pair, push it N times for weighting (this is not
          // the most efficient way to do this)
          for (var i = 0; i < series[x][1]; i++)
            iseries.push(+series[x][0]);
        } else {
          iseries.push(+series[x]);
        }
      }
    }
    if (!iseries.length) return [null, null, null];
    iseries.sort();
    var median;
    if (iseries.length % 2)
      median = iseries[(iseries.length - 1)/ 2];
    else
      median = iseries[iseries.length / 2];
    return median;
  }

  var buildinf;
  var series;
  var ctime = -1;
  var count = 0;

  var seriesdata = [];
  if (!involvedseries) {
    // Only one series, the overview data
    seriesdata.push(gGraphData);
  } else {
    for (var i in involvedseries)
      seriesdata.push(gFullData[involvedseries[i]]);
  }

  for (var seriesindex in seriesdata) {
    var sourceData = seriesdata[seriesindex];
    for (var ind in sourceData['builds']) {
      var b = sourceData['builds'][ind];
      if (start !== undefined && b['time'] < start) continue;
      if (stop !== undefined && b['time'] > stop) break;

      var time = groupin(b['time']);
      if (time != ctime) {
        pushdp(series, buildinf, ctime);
        count = 0;
        ctime = time;
        series = {};
        buildinf = { time: time };
      }

      // Full series uses non-merged syntax, which is just build['revision']
      // but we might be using overview data and hence merged syntax
      // (firstrev, lastrev)
      var rev = 'revision' in b ? b['revision'] : b['firstrev'];
      var lrev = 'revision' in b ? b['revision'] : b['lastrev'];
      var starttime = 'timerange' in b ? b['timerange'][0] : b['time'];
      var endtime = 'timerange' in b ? b['timerange'][1] : b['time'];
      count += 'count' in b ? b['count'] : 1;
      if (!buildinf['firstrev']) {
        buildinf['firstrev'] = rev;
        buildinf['timerange'] = [ starttime, endtime ];
      } else {
        buildinf['lastrev'] = lrev;
        buildinf['timerange'][1] = endtime;
      }
      for (var axis in this.axis) {
        if (!series[axis]) series[axis] = [];
        // Push all non-null datapoints onto list, pushdp() flattens
        // this list, finding its midpoint/min/max.
        var val = axis in sourceData['series'] ? sourceData['series'][axis][ind] : null;
        if (val && typeof(val) == "number") {
          series[axis].push(val);
        } else if (val) {
          // [ min, median, max ] formatted datapoint (already condensed). Push
          // it to series as [ median, count ] for flatten()
          series[axis].push([ val[1], count ]);
        }
      }
    }
  }
  pushdp(series, buildinf, ctime);

  // Push a dummy null point at the end of the series to force the zoom to end
  // exactly there
  builds.push({ time: stop, timerange: [ stop, stop ] });
  var seriesData = [];
  for (var axis in this.axis) {
    data[axis].push([ stop, null ]);
    seriesData.push({ name: axis, label: this.axis[axis], data: data[axis], buildinfo: builds });
  }

  return seriesData;
}

// Either zoom in on a datapoint or trigger a graph zoom or do nothing.
Plot.prototype.onClick = function(item) {
  if (item) {
    // Clicked an item, switch tooltip to build detail mode
    this.tooltip.buildDetail();
  } else if (this.highlighted) {
    // Clicked on highlighted zoom space, do a graph zoom

    // Extend the range if necessary to cover builds part of the condensed points.
    // Fixes, for instance, a condensed point with a timestamp of 'april 4th'
    // that contains builds through april 4th at 4pm. If your selection includes
    // that point, you expect to get all builds that that point represents
    var buildinfo = this.flot.getData()[0].buildinfo;
    var firstbuild;
    for (var i = 0; i < buildinfo.length; i++) {
      if (buildinfo[i]['time'] < this.highlightRange[0]) continue;
      if (buildinfo[i]['time'] > this.highlightRange[1]) break;
      if (!firstbuild) firstbuild = i;
    }
    var buildrange = getBuildTimeRange(buildinfo[firstbuild], buildinfo[Math.min(i, buildinfo.length - 1)]);
    var zoomrange = [];
    zoomrange[0] = Math.min(this.highlightRange[0], buildrange[0]);
    zoomrange[1] = Math.max(this.highlightRange[1], buildrange[1]);
    this.setZoomRange(zoomrange);
  }
}

Plot.prototype._drawAnnotations = function() {
  var self = this;
  this.annotations.empty();

  function includeAnno(anno) {
    if (gQueryVars['mobile'] && anno['mobile'] === false)
        return false;
    if (!gQueryVars['mobile'] && anno['desktop'] === false)
        return false;
    if (anno['whitelist'] && anno['whitelist'].indexOf(self.name) == -1)
        return false;
    return true;
  }

  function dateStamp(msg, time) {
    return '<div class="grey">' + prettyDate(time / 1000) + '</div>' + msg;
  }

  // Determine the pixels:time ratio for this zoom level
  var xaxis = this.flot.getAxes().xaxis;
  var secondsPerPixel = xaxis.c2p(1) - xaxis.c2p(0);
  var mergeTime = gAnnoMergeDist * secondsPerPixel * 1000;
  var mergedAnnotations = [];
  for (var i = 0; i < gAnnotations.length; i++) {
    if (!includeAnno(gAnnotations[i]))
      continue;
    var starttime = gAnnotations[i]['date'].getTime();
    var timesum = starttime;
    var msg = dateStamp(gAnnotations[i]['msg'], starttime);
    var elements = 1;
    while (i + 1 < gAnnotations.length &&
           gAnnotations[i + 1]['date'].getTime() - starttime < mergeTime) {
      i++;
      var merge = gAnnotations[i];
      if (!includeAnno(merge))
        continue;
      elements++;
      var mergetime = merge['date'].getTime();
      timesum += mergetime;
      msg += "<hr>" + dateStamp(merge['msg'], mergetime);
    }
    mergedAnnotations.push({ 'date': new Date(timesum / elements),
                             'msg': msg });
  }
  for (var i = 0; i < mergedAnnotations.length; i++) {
    (function () {
      var anno = mergedAnnotations[i];

      var date = anno['date'];

      var div = $.new('div').addClass('annotation').text('?');
      self.annotations.append(div);
      var tooltiptop = parseInt(div.css('padding-top')) * 2 + 5
                     + parseInt(div.css('height'))
                     + parseInt(self.annotations.css('top'))
                     + self.flot.getPlotOffset().top
                     + self.obj.offset().top - self.container.offset().top;
      var divwidth = parseInt(div.css('padding-left'))
                   + parseInt(div.css('width'));
      var left = xaxis.p2c(date.getTime() / 1000) - divwidth / 2;

      if (left + divwidth + 5 > self.flot.width() ||
          left - 5 < 0) {
        div.remove();
        return;
      }

      div.css('left', left);

      div.mouseover(function() {
        // Don't hijack a tooltip that's in the process of zooming
        if (self.tooltip.isZoomed())
          return;
        self.tooltip.empty();
        self.tooltip.append(anno['msg']);
        var x = left
              - parseInt(self.tooltip.obj.css('width')) / 2
              - parseInt(self.tooltip.obj.css('padding-left'))
              - gTooltipOffset
              + divwidth / 2
              + self.flot.getPlotOffset().left;
        self.tooltip.hover(x, tooltiptop);
      });
      div.mouseout(function() { self.tooltip.unHover(); });
    })();
  }
}

// Shows the zoom/highlight bar centered [location] pixels from the left of the
// graph.
//
// EX To turn a mouse event into graph coordinates:
// var location = event.pageX - this.flot.offset().left
//                + this.flot.getPlotOffset().left;
Plot.prototype.showHighlight = function(location, width) {
  if (!this.highlighted) {
    this.zoomSelector.stop().fadeTo(250, 1);
    this.highlighted = true;
  }

  this._highlightLoc = location;
  this._highlightWidth = width;

  var minZoomDays = 3;
  var xaxis = this.flot.getAxes().xaxis;
  if (xaxis.max - xaxis.min <= minZoomDays * 24 * 60 * 60) {
    this.highlighted = false;
    this.zoomSelector.stop().fadeTo(50, 0);
    return;
  }

  var off = this.flot.getPlotOffset();
  var left = location - width / 2;
  var overflow = left + width - this.flot.width() - off.left;
  var underflow = off.left - left;

  if (overflow > 0) {
    width = Math.max(width - overflow, 0);
  } else if (underflow > 0) {
    left += underflow;
    width = Math.max(width - underflow, 0);
  }

  // Calculate the x-axis range of the data we're highlighting
  this.highlightRange = [ xaxis.c2p(left - off.left), xaxis.c2p(left + width - off.left) ];

  this.zoomSelector.css({
    left: left + 'px',
    width: width + 'px'
  });
}

Plot.prototype.hideHighlight = function() {
  if (this.highlighted) {
    this.highlighted = false;
    this.zoomSelector.stop().fadeTo(250, 0);
  }
}

// If we're hovering over a point, show a tooltip. Otherwise, show the
// zoom selector if we're not beyond our zoom-in limit
Plot.prototype.onHover = function(item, pos) {
  if (this.tooltip.isZoomed()) {
    return;
  }
  var self = this;
  if (item &&
      (!this.hoveredItem || (item.dataIndex !== this.hoveredItem.dataIndex))) {
    this.hideHighlight();
    this.tooltip.showBuild(item.series.label,
                           item.series.data,
                           item.series.buildinfo,
                           item.dataIndex,
                           item.series.name);

    // Tooltips move relative to the graphContainer
    var offset = this.container.offset();
    this.tooltip.hover(item.pageX - offset.left, item.pageY - offset.top, this.hoveredItem ? true : false);
  } else if (!item) {
    if (this.hoveredItem) {
      // Only send unhover to the tooltip after we have processed all
      // graphhover events, and the tooltip has processed its mouseover events
      window.setTimeout(function () {
        if (!self.hoveredItem) {
          self.tooltip.unHover();
        }
      }, 0);
    }
    // Move hover highlight for zooming
    var left = pos.pageX - this.flot.offset().left + this.flot.getPlotOffset().left;
    this.showHighlight(left, gHighlightWidth);
  }
  this.hoveredItem = item;
}

//
// Init. Load initial gGraphData, draw main page graphs
//
$(function () {
  // Load graph data
  // Allow selecting an alternate series
  var series = 'areweslimyet';
  if ('series' in gQueryVars && gQueryVars['series'].match('^[a-z0-9\-_]+$'))
    series = gQueryVars['series'];
  var url = '/data/' + series + '.json';

  $.ajax({
    url: url,
    xhr: dlProgress,
    success: function (data) {
      //
      // Graph data arrived, do additional processing and create plots
      //
      gGraphData = data;
      // Calculate gDataRange.  The full range of gGraphData can have a number
      // of superfluous builds that have null for all series values we care
      // about. For instance, the mobile series all start Dec 2012, so all
      // builds prior to that are not useful in mobile mode.
      gDataRange = [ null, null ];
      for (var graph in gSeries) {
        for (var series in gSeries[graph]) {
          for (var ind = 0; ind < gGraphData['builds'].length; ind++) {
            var val = gGraphData['series'][series][ind];
            if (val instanceof Array)
              val = val[1]; // [min, median, max] data
            if (val !== null) {
              var b = gGraphData['builds'][ind];
              var buildstart = 'timerange' in b ? b['timerange'][0] : b['time'];
              var buildstop = 'timerange' in b ? b['timerange'][1] : b['time'];
              if (gDataRange[0] === null || buildstart < gDataRange[0])
                gDataRange[0] = buildstart;
              if (gDataRange[1] === null || buildstop > gDataRange[1])
                gDataRange[1] = buildstop;
            }
          }
        }
        if (gDataRange[0] === null || gDataRange[1] === null) {
          logError("No valid data in the full range!");
        } else if (gDataRange[0] == gDataRange[1]) {
          // Only one timestamp, bump the range out around it so flot does not
          // have a heart attack
          gDataRange[0] -= 60 * 60 * 24 * 7;
          gDataRange[1] += 60 * 60 * 24 * 7;
        }
      }
      logMsg("Useful data range is [ " + gDataRange + " ]");
      $('#graphs h3').remove();
      for (var graphname in gSeries) {
        gZoomSyncPlots[graphname] = new Plot(graphname, $('#graphs'));
      }
    },
    error: function(xhr, status, error) {
      $('#graphs h3').text("An error occured while loading the graph data (" + url + ")");
      $('#graphs').append($.new('p', null, { 'text-align': 'center', color: '#F55' }).text(status + ': ' + error));
    },
    dataType: 'json'
  });

  // Handler to close zoomed tooltips upon clicking outside of them
  $('body').bind('click', function(e) {
    if (!$(e.target).is('.tooltip') && !$(e.target).parents('.graphContainer').length)
      $('.tooltip.zoomed').each(function(ind,ele) {
        $(ele).data('owner').unzoom();
      });
  });
});
