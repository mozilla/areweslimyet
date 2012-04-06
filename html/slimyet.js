
/*
 * Copyright © 2012 Mozilla Corporation
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/.
 */

"use strict";

// Query (search) vars. (Because screw the hashbang, I suppose)
var gQueryVars = (function () {
  var ret = {};
  if (document.location.search) {
    var vars = document.location.search.slice(1).split('&');
    for (var x in vars) {
      x = vars[x].split('=');
      ret[decodeURIComponent(x[0])] = x.length > 1 ? decodeURIComponent(x[1]) : true;
    }
  }
  return ret;
})();

// Width in pixels of highlight (zoom) selector
var gHighlightWidth = gQueryVars['zoomwidth'] ? +gQueryVars['zoomwidth'] : 400;

// Coalesce datapoints to keep them under this many per zoom level.
// Default to 150, or 0 (disabled) if nocondense is supplied
var gMaxPoints = gQueryVars['maxpoints'] ? +gQueryVars['maxpoints'] : (gQueryVars['nocondense'] ? 0 : 150);

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
var gReleases = [
  {dateStr: "2011-03-03", name: "FF 5"},
  {dateStr: "2011-04-12", name: "FF 6"},
  {dateStr: "2011-05-24", name: "FF 7"},
  {dateStr: "2011-07-05", name: "FF 8"},
  {dateStr: "2011-08-16", name: "FF 9"},
  {dateStr: "2011-09-27", name: "FF 10"},
  {dateStr: "2011-11-08", name: "FF 11"},
  {dateStr: "2011-12-20", name: "FF 12"},
  {dateStr: "2012-01-31", name: "FF 13"},
  {dateStr: "2012-03-13", name: "FF 14"},
  {dateStr: "2012-04-24", name: "FF 15"},
  {dateStr: "2012-06-05", name: "FF 16"},
  {dateStr: "2012-07-17", name: "FF 17"},
  {dateStr: "2012-08-28", name: "FF 18"},
  {dateStr: "2012-10-09", name: "FF 19"}
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
    'EndMemoryResidentSettledV2':    "RSS: After TP5, tabs closed [+30s]"
  },
  "Explicit Memory" : {
    'StartMemoryV2':         "Explicit: Fresh start",
    'StartMemorySettledV2':  "Explicit: Fresh start [+30s]",
    'MaxMemoryV2':           "Explicit: After TP5",
    'MaxMemorySettledV2':    "Explicit: After TP5 [+30s]",
    'MaxMemoryForceGCV2':    "Explicit: After TP5 [+30s, forced GC]",
    'EndMemoryV2':           "Explicit: After TP5, tabs closed",
    'EndMemorySettledV2':    "Explicit: After TP5, tabs closed [+30s]"
  },
  "Miscellaneous Measurements" : {
    'MaxHeapUnclassifiedV2':  "Heap Unclassified: After TP5 [+30s]",
    'MaxJSV2':                "JS: After TP5 [+30s]",
    'MaxImagesV2':            "Images: After TP5 [+30s]"
  }
};

/*
 * Hidden, these should be given their own page or something, as they are useful
 * for regression tracking. The FAQ needs to explain them, however
  "All-At-Once Test :: Resident Memory" : {
    'StartMemoryResident':         "RSS: Fresh start",
    'StartMemoryResidentSettled':  "RSS: Fresh start [+30s]",
    'MaxMemoryResident':           "RSS: After TP5",
    'MaxMemoryResidentSettled':    "RSS: After TP5 [+30s]",
    'MaxMemoryResidentForceGC':    "RSS: After TP5 [+30s, forced GC]",
    'EndMemoryResident':           "RSS: After TP5, tabs closed",
    'EndMemoryResidentSettled':    "RSS: After TP5, tabs closed [+30s]"
  },
  "All-At-Once Test :: Explicit Memory" : {
    'StartMemory':         "Explicit: Fresh start",
    'StartMemorySettled':  "Explicit: Fresh start [+30s]",
    'MaxMemory':           "Explicit: After TP5",
    'MaxMemorySettled':    "Explicit: After TP5 [+30s]",
    'MaxMemoryForceGC':    "Explicit: After TP5 [+30s, forced GC]",
    'EndMemory':           "Explicit: After TP5, tabs closed",
    'EndMemorySettled':    "Explicit: After TP5, tabs closed [+30s]"
  },
 */

// gGraphData pulls /data/<series>.json which has a *condensed* series of builds
// and associated data-lines. After a certain zoom level we need to pull in the
// full-resolution data into gFullData. gGraphData['allseries'] contains info on
// the sub-series that can be fetched for gFullData.
//
// The pre-condensed datapoints and ones we fetch ourselves all have
// min/median/max data, and the revision-range and time-range. See the
// /data/areweslimyet.json file.
//
// Plot._getInvolvedSeries() - Determines if our zoom level justifies using
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

  // TODO Better selection of nodes that should show Mem/Pct
  var showMem = depth >= 2;
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
    if (node == '_val')
      continue;
    rows.push(node);
  }
  if (showMem) {
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
    var leaf = typeof(data[node]) == 'number';
    var treeNode = $.new('div')
                    .addClass('treeNode')
                    .data('nodeData', data[node])
                    .data('depth', depth + 1);
    var nodeTitle = $.new('div')
                     .addClass('treeNodeTitle')
                     .appendTo(treeNode);

    // Add value if inside a memNode
    var val = defval(data[node]);
    if (showMem && val != null) {
      // Value
      $.new('span').addClass('treeValue')
                  .text(formatBytes(val))
                  .appendTo(nodeTitle);
      // Percentage
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

  this.obj.data('owner', this);
  this.onUnzoomFuncs = [];
}

Tooltip.prototype.isZoomed = function () { return this.obj.is('.zoomed'); }

Tooltip.prototype.append = function(obj) {
  this.content.append(obj);
}

Tooltip.prototype.empty = function() {
  this.content.empty();
}

Tooltip.prototype.hover = function(x, y, nofade) {
  if (this.isZoomed())
    return;

  var poffset = this.obj.parent().offset();

  var h = this.obj.outerHeight();
  var w = this.obj.outerWidth();
  var pad = 5;
  // Lower-right of cursor
  var top = y + pad;
  var left = x + pad;
  // Move above cursor if too far down
  if (window.innerHeight + document.body.scrollTop < poffset.top + top + h + 30)
    top = y - h - pad;
  // Move left of cursor if too far right
  if (window.innerWidth + document.body.scrollLeft < poffset.left + left + w + 30)
    left = x - w - pad;

  this.obj.css({
    top: top,
    left: left
  });

  // Show tooltip
  if (!nofade)
    this.obj.stop().fadeTo(200, 1);
}

Tooltip.prototype.unHover = function(nofade) {
  if (this.isZoomed())
    return;
  this.obj.stop().fadeTo(200, 0, function () { $(this).hide(); });
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
  $.new('a', { class: 'closeButton', href: '#' })
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
    if (success instanceof Function) success.apply(null);
  } else {
    if (!(dataname in gPendingFullData)) {
      gPendingFullData[dataname] = { 'success': [], 'fail': [] };
      $.ajax({
        url: './data/' + dataname + '.json',
        success: function (data) {
          gFullData[dataname] = data;
          for (var i in gPendingFullData[dataname]['success'])
            gPendingFullData[dataname]['success'][i].call(null);
          delete gPendingFullData[dataname];
        },
        error: function(xhr, status, error) {
          for (var i in gPendingFullData[dataname]['fail'])
            gPendingFullData[dataname]['fail'][i].call(null);
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
      url: './data/' + buildname + '.json',
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

  this.axis = gSeries[name];
  this.zoomed = false;
  var firstb = gGraphData['builds'][0];
  var lastb = gGraphData['builds'][gGraphData['builds'].length - 1];

  // If the builds specify a timerange that extends beyond the average time,
  // use that. (Note that the average time does not need to be inside the
  // timerange -- overview data groups it by day @ midnight)
  this.dataRange = this._getBuildTimeRange(firstb, lastb);

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

  this.tooltip = new Tooltip(this.container);
  var self = this;
  this.obj.bind("plotclick", function(event, pos, item) { self.onClick(item); });
  this.obj.bind("plothover", function(event, pos, item) { self.onHover(item, pos); });
  this.obj.bind("mouseout", function(event) { self.hideHighlight(); });
}

// Get the full time range covered by two (possibly condensed) build_info structs
Plot.prototype._getBuildTimeRange = function(firstbuild, lastbuild)
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
    if (range === undefined) {
      zoomOut = true;
      range = this.dataRange;
    }

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
    var fullseries = self._getInvolvedSeries(range);
    var pending = 0;
    for (var x in fullseries) {
      if (!(fullseries[x] in gFullData)) {
        pending++;
        var self = this;
        getFullSeries(fullseries[x], function () {
          if (--pending == 0 && self.zoomed)
            self.setZoomRange(self.zoomRange, true);
        });
      }
    }

    this.zoomRange = range;
    var newseries = this._buildSeries(range[0], range[1]);
    this.flot.setData(newseries);
    this.flot.setupGrid();
    this.flot.draw();

    // The highlight has the wrong range now that we mucked with the graph
    if (this.highlighted)
      this.showHighlight(this._highlightLoc, this._highlightWidth);

    // Sync all other plots
    if (!nosync)
      for (var x in gZoomSyncPlots)
        if (gZoomSyncPlots[x] != this)
          gZoomSyncPlots[x].setZoomRange(zoomOut ? undefined : range, true);
}

// If this range is 'zoomed' enough to warrant using full-resolution data
// (based on gMaxPoints), return the list of gFullData series names that would
// be needed. Return false if overview data is sufficient for this range.
// It's up to the caller to call getFullSeries(name) to start downloading any
// of these that arn't downloaded.
Plot.prototype._getInvolvedSeries = function(range) {
  var ret = [];
  var groupdist = gMaxPoints < 1 ? 1 : (Math.round((range[1] - range[0]) / gMaxPoints));

  // Unless the requested grouping distance is < 80% of the overview data's
  // distance, don't pull in more
  if (!gQueryVars['nocondense'] && groupdist / gGraphData['condensed'] > 0.8)
    return null;

  for (var x in gGraphData['allseries']) {
    var s = gGraphData['allseries'][x];
    if (range[1] > s['fromtime'] && range[0] < s['totime'])
      ret.push(s['dataname']);
  }
;
  return ret;
}

// Takes two timestamps and builds a list of series based on this plot's axis
// suitable for passing to flot - condensed to try to hit gMaxPoints.
// Uses series returned by _getInvolvedSeries *if they are all downloaded*,
// otherwise always uses overview data.
// See comment about gFullData at top of file
Plot.prototype._buildSeries = function(start, stop) {
  var self = this; // for closures
  var involvedseries = this._getInvolvedSeries([start, stop]);

  // Don't use the involved series if they're not all downloaded
  for (var x in involvedseries) {
    if (!gFullData[involvedseries[x]]) {
      involvedseries = false;
      break;
    }
  }

  var builds = [];
  var ranges = {};
  var data = {};

  for (var axis in this.axis) {
    ranges[axis] = [];
    data[axis] = [];
  }

  // Grouping distance
  var groupdist = gMaxPoints < 1 ? 1 : (Math.round((stop - start) / gMaxPoints));

  // Points might be [min, median, max], or just a number if it only
  // represents one datapoint.
  function pval(point, ind) {
    var ret = (point instanceof Array) ? point[ind] : point;
    return (ret === null) ? ret : +ret;
  }

  function pushdp(series, buildinf, ctime) {
    // Push a datapoint onto builds/ranges/data
    if (ctime != -1) {
      if (!buildinf['lastrev']) {
        // Only one datapoint, use specific time and remove
        // timerange
        buildinf['time'] = buildinf['timerange'][0];
        delete buildinf['timerange']
      }
      builds.push(buildinf);
      for (axis in self.axis) {
        var flat = flatten(series[axis]);
        data[axis].push([ +buildinf['time'], flat[1] ]);
        ranges[axis].push([flat[0], flat[2]]);
      }
    }
  }
  function groupin(timestamp) {
    return timestamp - (timestamp % groupdist);
  }
  // Given a list of numbers, return [min, median, max]
  function flatten(series) {
    var iseries = [];
    for (var x in series) {
      if (series[x] !== null) iseries.push(+series[x]);
    }
    if (!iseries.length) return [null, null, null];
    iseries.sort();
    var median;
    if (iseries.length % 2)
      median = iseries[(iseries.length - 1)/ 2];
    else
      median = iseries[iseries.length / 2];
    return [iseries[0], median, iseries[iseries.length - 1]];
  }
  if (involvedseries && involvedseries.length) {
    // Mode 1:
    // Have full data, coalesce it to the desired density ourselves
    logMsg("Building series using full data");
    var buildinf;
    var series;
    var ctime = -1;
    for (var seriesindex in involvedseries) {
      var sourceData = gFullData[involvedseries[seriesindex]];
      for (var ind in sourceData['builds']) {
        var b = sourceData['builds'][ind];
        if (start !== undefined && b['time'] < start) continue;
        if (stop !== undefined && b['time'] > stop) break;

        var time = groupin(b['time']);
        if (time != ctime) {
          pushdp(series, buildinf, ctime);
          ctime = time;
          series = {};
          buildinf = { time: time };
        }

        var rev = b['revision'];
        if (!buildinf['firstrev']) {
          buildinf['firstrev'] = b['revision'];
          buildinf['timerange'] = [ b['time'], null ];
        } else {
          buildinf['lastrev'] = b['revision'];
          buildinf['timerange'][1] = b['time'];
        }
        for (var axis in this.axis) {
          if (!series[axis]) series[axis] = [];
          // Push all non-null datapoints onto list, pushdp() flattens
          // this list, finding its midpoint/min/max.
          var val = sourceData['series'][axis][ind];
          if (val) series[axis].push(val);
        }
      }
    }
    pushdp(series, buildinf, ctime);

  } else {
    // Mode 2:
    // Using overview data, which is already condensed.
    // Merge every N points to get close to our desired density.
    var merge = Math.max(Math.round(groupdist / gGraphData['condensed']), 1);
    logMsg("Building series using overview data, merging every " + merge);
    var nbuilds = gGraphData['builds'].length;
    for (var i = 0; i < nbuilds; i += merge) {
      var b = gGraphData['builds'][i];
      var ilast = i + merge - 1 < nbuilds ? i + merge - 1 : nbuilds - 1;
      var blast = gGraphData['builds'][ilast];

      if (b['time'] < start) continue;
      if (blast['time'] > stop) break;

      var time;
      var totalbuilds;
      if (merge > 1) {
        time = 0;
        for (var x = 0; x + i <= ilast; x++) {
          time += +gGraphData['builds'][x + i]['time'];
          totalbuilds += +gGraphData['builds'][x + i]['count'];
        }
        time = Math.round(time / (ilast - i + 1));
        var newb = { firstrev: b['firstrev'] };
        newb['time'] = time;

        newb['lastrev'] = blast['lastrev'] ? blast['lastrev'] : blast['firstrev'];
        var from = b['timerange'] ? b['timerange'][0] : b['time'];
        var to = blast['timerange'] ? blast['timerange'][1] : blast['time'];
        newb['timerange'] = [ from, to ];
        builds.push(newb);
      } else {
        builds.push(b);
        time = b['time'];
      }

      // Roughly select the median point based on number of builds in each
      // point we're merging. This is less-bad than averaging medians
      var count = 0;
      for (var x = 0; x + i <= ilast; x++) {
        var next = +gGraphData['builds'][x + i]['count'];
        if (next + count > totalbuilds / 2) break;
        count += next;
      }
      var medianbuild = Math.min(x + i, ilast);

      for (var axis in this.axis) {
        var median = pval(gGraphData['series'][axis][medianbuild], 1);
        var min = pval(gGraphData['series'][axis][i], 0);
        var max = pval(gGraphData['series'][axis][ilast], 2);
        data[axis].push([ time, median ]);
        ranges[axis].push([ min, max ]);
      }
    }
  }

  var seriesData = [];
  for (var axis in this.axis)
    seriesData.push({ name: axis, range: ranges[axis], label: this.axis[axis], data: data[axis], buildinfo: builds });

  return seriesData;
}

// Either zoom in on a datapoint or trigger a graph zoom or do nothing.
Plot.prototype.onClick = function(item) {
  if (item) {
    // Clicked on an item - zoom the tooltip and load full data dump
    var zoomedCallback;
    this.tooltip.zoom();
    var loading = $.new('h2', null, {
      display: 'none',
      'text-align': 'center',
    }).text('Loading test data...')
    this.tooltip.append(loading);
    loading.fadeIn();

    // Load per build data
    var canceled = false;
    var revision = item.series.buildinfo[item.dataIndex]['firstrev'];
    var self = this;
    getPerBuildData(revision, function () {
      // On get data (can be immediate)
      if (canceled) { return; }

      // Build zoomed tooltip
      var series_info = gGraphData['series_info'][item.series.name];
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

      loading.css({ 'width' : '100%', 'position': 'absolute' }).fadeOut(250);

      var title;
      if ('lastrev' in item.series.buildinfo[item.dataIndex])
        title = revision.slice(0,12) + " @ " + series_info['test'];
      else
        title = series_info['test'];
      var memoryTree = makeMemoryTree(title, nodes, datapoint);

      self.tooltip.append(memoryTree);
      memoryTree.fadeIn();
    }, function (error) {
      // On failure
      loading.text("An error occured while loading the datapoint");
      self.tooltip.append($.new('p', null, { color: '#F55' }).text(status + ': ' + error));
    });
    // Cancel loading if tooltip is closed before the callback
    this.tooltip.onUnzoom(function () { canceled = true; });
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
    var buildrange = this._getBuildTimeRange(buildinfo[firstbuild], buildinfo[Math.min(i, buildinfo.length - 1)]);
    var zoomrange = [];
    zoomrange[0] = Math.min(this.highlightRange[0], buildrange[0]);
    zoomrange[1] = Math.max(this.highlightRange[1], buildrange[1]);
    this.setZoomRange(zoomrange);
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
  function revlink(rev) {
    return $.new('a')
            .attr('href', "http://hg.mozilla.org/mozilla-central/rev/" + rev)
            .text(rev);
  }
  if ((!item || item !== this.hoveredItem) && !this.tooltip.isZoomed()) {
    if (item) {
      this.hideHighlight();
      // Tooltip Content
      this.tooltip.empty();
      var buildinfo = item.series.buildinfo[item.dataIndex];
      var rev = buildinfo['firstrev'].slice(0,12);

      // Label
      this.tooltip.append($.new('h3').text(item.series['label']));
      // Build link / time
      var ttinner = $.new('p');
      ttinner.append($.new('p').text(formatBytes(item.datapoint[1])));
      ttinner.append($.new('b').text('build '));
      ttinner.append(revlink(rev));
      if (buildinfo['lastrev']) {
        ttinner.append(' .. ');
        ttinner.append(revlink(buildinfo['lastrev'].slice(0,12)));
      }
      ttinner.append($.new('p').text(prettyDate(item.datapoint[0])));
      this.tooltip.append(ttinner);

      // Tooltips move relative to the graphContainer
      var offset = this.container.offset();
      this.tooltip.hover(item.pageX - offset.left, item.pageY - offset.top, this.hoveredItem ? true : false);
    } else {
      if (this.hoveredItem)
        this.tooltip.unHover();
      // Move hover highlight for zooming
      var left = pos.pageX - this.flot.offset().left + this.flot.getPlotOffset().left;
      this.showHighlight(left, gHighlightWidth);
    }
    this.hoveredItem = item;
  }
}

//
// Init. Load initial gGraphData, draw main page graphs
//
$(function () {
  // Load graph data
  // Allow selecting an alternate series
  var series = gQueryVars['series'] ? gQueryVars['series'] : 'areweslimyet';
  var url = './data/' + series + '.json';

  $.ajax({
    url: url,
    success: function (data) {
      gGraphData = data;
      function makePlots() {
        $('#graphs h3').remove();
        for (var graphname in gSeries) {
          gZoomSyncPlots[graphname] = new Plot(graphname, $('#graphs'));
        }
      }
      if (gQueryVars['nocondense']) {
        // Load all graph data, all the time, not using the condensed 'overview'
        // data
        $('#graphs h3').text("Loading all the things [nocondense]...");
        var pending = 0;
        for (var x in gGraphData['allseries']) {
          pending++;
          getFullSeries(gGraphData['allseries'][x]['dataname'], function () {
            if (--pending == 0) makePlots();
          });
        }
      } else {
        makePlots();
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
