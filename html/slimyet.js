
/*
 * Copyright © 2012 Mozilla Corporation
 * 
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/.
 */

"use strict";

jQuery.new = function(e, attrs, css) {
  var ret = jQuery(document.createElement(e));
  if (attrs) ret.attr(attrs);
  if (css) ret.css(css);
  return ret;
};

// 10-class paired qualitative color scheme from http://colorbrewer2.org/.
var gDefaultColors = [
  "#1F78B4",
  "#33A02C",
  "#E31A1C",
  "#FF7F00",
  "#6A3D9A",
  "#A6CEE3",
  "#B2DF8A",
  "#FB9A99",
  "#FDBF6F",
  "#CAB2D6",
];

// Which series from series.json to graph where with what label
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
    'MaxMemoryV2':           "Explicit: TP5 opened in 30 tabs",
    'MaxMemorySettledV2':    "Explicit: TP5 opened in 30 tabs [+30s]",
    'MaxMemoryForceGCV2':    "Explicit: TP5 opened in 30 tabs [+30s, forced GC]",
    'EndMemoryV2':           "Explicit: Tabs closed",
    'EndMemorySettledV2':    "Explicit: Tabs closed [+30s]"
  },
  "All-At-Once Test :: Resident Memory" : {
    'StartMemoryResident':         "RSS: Fresh start",
    'StartMemoryResidentSettled':  "RSS: Fresh start [+30s]",
    'MaxMemoryResident':           "RSS: TP5 opened in 30 tabs",
    'MaxMemoryResidentSettled':    "RSS: TP5 opened in 30 tabs [+30s]",
    'MaxMemoryResidentForceGC':    "RSS: TP5 opened in 30 tabs [+30s, forced GC]",
    'EndMemoryResident':           "RSS: Tabs closed",
    'EndMemoryResidentSettled':    "RSS: Tabs closed [+30s]"
  },
  "All-At-Once Test :: Explicit Memory" : {
    'MaxMemory':           "Explicit: TP5 opened in 30 tabs",
    'MaxMemorySettled':    "Explicit: TP5 opened in 30 tabs [+30s]",
    'MaxMemoryForceGC':    "Explicit: TP5 opened in 30 tabs [+30s, forced GC]",
    'StartMemory':         "Explicit: Fresh start",
    'StartMemorySettled':  "Explicit: Fresh start [+30s]",
    'EndMemory':           "Explicit: Tabs closed",
    'EndMemorySettled':    "Explicit: Tabs closed [+30s]"
  },
  "Possibly Interesting Things" : {
    'MaxHeapUnclassifiedV2':  "Heap Unclassified: TP5 opened in 30 tabs [+30s]",
    'MaxJSV2':                "JS: TP5 opened in 30 tabs [+30s]",
    'MaxImagesV2':            "Images: TP5 opened in 30 tabs [+30s]"
  }
};

// Filled with /data/series.json
// FIXME this comment is wrong
// Contains info about graphs to create and sparse data for initial graphing.
// When we zoom in, ajax requests further data.
var gGraphData;
var gPerBuildData = {};

//
// Utility
//

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

function prettyFloat(aFloat) {
  var ret = Math.round(aFloat * 100).toString();
  if (ret == "0") return ret;
  if (ret.length < 3)
    ret = (ret.length < 2 ? "00" : "0") + ret;
  
  var clen = (ret.length - 2) % 3;
  ret = ret.slice(0, clen) + ret.slice(clen, -2).replace(/[0-9]{3}/g, ',$&') + '.' + ret.slice(-2);
  return clen ? ret : ret.slice(1);
}

// TODO add a pad-to-size thing
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

//
// For the about:memory-esque display
//

// TODO document selectedNode return val
function treeExpandNode(node, noanimate) {
  if (!node.is('.hasChildren')) return;
  
  var subtree = node.find('.subtree');
  if (!subtree.length) {
    var subtree = $.new('div').addClass('subtree').hide();
    renderMemoryTree(subtree, node.data('nodeData'),
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

function treeCollapseNode(node) {
  node.children('.subtree').slideUp(250);
  node.children('.treeNodeTitle').find('.treeExpandClicker').text('[+]');
}

function treeToggleNode(node) {
  if (node.find('.subtree:visible').length)
    treeCollapseNode(node);
  else
    treeExpandNode(node);
}

// TODO document args
function renderMemoryTree(target, data, select, depth) {
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
    return obj['_val'] !== undefined ? obj['_val']
           : (obj['_sum'] !== undefined ? obj['_sum'] : null);
  }
  
  // Sort nodes
  var rows = [];
  for (var node in data) {
    if (node == '_val' || node == '_sum')
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
    var title = node, subtitle;
    if (subtitle = /^(.+)\((.+)\)$/.exec(node)) {
      node = subtitle[1];
      subtitle = subtitle[2];
    }
    var label = $.new('span').addClass('treeNodeLabel')
                             .appendTo(nodeTitle).text(node);
    if (subtitle) {
      $.new('span').addClass('subtitle').text(' '+subtitle).appendTo(label);
    }

    // Add treeExpandClicker and click handler if node has children
    var expandClick = $.new('span').addClass('treeExpandClicker');
    nodeTitle.prepend(expandClick);
    for (var x in data[node]) {
      if (x !== '_val' && x !== '_sum') {
        expandClick.text('[+]');
        nodeTitle.click(function () { treeToggleNode($(this).parent()); });
        treeNode.addClass('hasChildren');
        break;
      }
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
    
  this.obj.show();
  this.obj.stop().addClass('zoomed').animate({
    width: '110%',
    height: '100%',
    left: '-5%',
    top: '-5%',
    opacity: 1
  }, 500, null, callback);
  
  // Close button
  var self = this;
  $.new('a', { class: 'closeButton', href: '#' }).addClass('closeButton')
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
    var self = this;
    this.obj.animate({
        width: '50%',
        height: '50%',
        top: '25%',
        left: '25%',
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
// Creates a plot, appends it to #graphs
// - axis -> { 'AxisName' : 'Nicename', ... }
//
function Plot(axis) {
  if (!this instanceof Plot) {
    logError("Plot() used incorrectly");
    return;
  }

  this.axis = axis;
  this.zoomed = false;
  this.dataRange = [ gGraphData['builds'][0]['time'],
                     gGraphData['builds'][gGraphData['builds'].length - 1]['time'] ];
  this.zoomRange = this.dataRange;
  
  this.obj = $.new('div').addClass('graph').appendTo($('#graphs'));
  this.flot = $.plot(this.obj,
    // Data
    this._buildSeries(),
    // Options
    {
      series: {
        lines: { show: true },
        points: { show: true }
      },
      grid: {
        color: "#FFF",
        hoverable: true,
        clickable: true
      },
      xaxis: {
        tickFormatter: function(val, axis) {
          return new Date(val * 1000).toDateString();
        }
      },
      yaxis: {
        ticks: function(axis) {
          var approxNumTicks = 10;
          var interval = axis.max / approxNumTicks;

          // Round interval up to nearest power of 2.
          interval = Math.pow(2, Math.ceil(Math.log(interval) / Math.log(2)));

          // Round axis.max up to the next interval.
          var max = Math.ceil(axis.max / interval) * interval;

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
        backgroundColor: "#000",
        margin: 10,
        position: 'nw',
        backgroundOpacity: 0.4
      },
      colors: gDefaultColors
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
                       .text("[zoom]")
                       .insertBefore(fcanvas);
  // For proper layering
  $(fcanvas).css('position', 'relative');
  
  //
  // Graph Tooltip
  //

  this.tooltip = new Tooltip(this.obj);
  var self = this;
  this.obj.bind("plotclick", function(event, pos, item) { self.onClick(item); });
  this.obj.bind("plothover", function(event, pos, item) { self.onHover(item, pos); });
  this.obj.bind("mouseout", function(event) { self.hideHighlight(); });
}

// Zoom this graph to given range. If called with no arguments, zoom all the way
// back out. range is of format [x1, x2]. this.dataRange contains the range of
// all data, this.zoomRange contains currently zoomed range if this.zoomed is
// true.
Plot.prototype.setZoomRange = function(range) {
    var zoomOut = false;
    if (range === undefined) {
      zoomOut = true;
      range = this.dataRange;
    }
    
    var self = this;
    if (this.zoomed && zoomOut) {
      // Zooming back out, remove close button
      this.zoomed = false;
      this.obj.children('.closeButton').remove();
    } else if (!this.zoomed && !zoomOut) {
      // Zoomed out -> zoomed in. Add close button
      this.zoomed = true;
      self.obj.append($.new('div').addClass('closeButton').text('[zoom out]').click(function () {
        self.setZoomRange();
      }));
    }

    this.zoomRange = range;
    var newseries = this._buildSeries(range[0], range[1]);
    this.flot.setData(newseries);
    this.flot.setupGrid();
    this.flot.draw();
    // setupGrid() reparents the grid, so we need to reparent the tooltip
    // such that it is last in the z-ordering
    this.tooltip.obj.appendTo(this.obj);
}

// RebuildsFIXME FIXME FIXME
Plot.prototype._buildSeries = function(start, stop) {
  var seriesData = [];
  if (start === undefined)
    start = gGraphData['builds'][0]['time'];
  if (stop == undefined)
    stop = gGraphData['builds'][gGraphData['builds'].length - 1]['time'];
  
  for (var axis in this.axis) {
    var series = [];
    var buildinfo = [];
    for (var ind in gGraphData['builds']) {
      var b = gGraphData['builds'][ind];
      if (b['time'] < start) continue;
      if (b['time'] > stop) break;
      series.push([ b['time'], gGraphData['series'][axis][ind] ]);
      buildinfo.push(b);
    }
    seriesData.push({ name: axis, label: this.axis[axis], data: series, buildinfo: buildinfo });
  }
  return seriesData;
}

Plot.prototype.onClick = function(item) {
  if (item) {
    // Zoom in on item
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
    var revision = item.series.buildinfo[item.dataIndex]['revision'];
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
      
      var memoryTree = $.new('div', { class: 'memoryTree' }, { display: 'none' });
      loading.css({ 'width' : '100%', 'position': 'absolute' }).fadeOut(250);
      
      // memoryTree title
      var treeTitle = $.new('div', { class: 'treeTitle' }).appendTo(memoryTree);
      $.new('h3').text('Part of test '+series_info['test'])
                 .appendTo(treeTitle);
      // datapoint subtitle
      $.new('div').addClass('highlight')
                  .text(datapoint.replace(/\//g, ' -> '))
                  .appendTo(treeTitle);
      renderMemoryTree(memoryTree, nodes, datapoint);
      
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
    this.setZoomRange(this.highlightRange);
  }
}

Plot.prototype.showHighlight = function(location, width) {
  if (!this.highlighted) {
    this.zoomSelector.stop().fadeTo(250, 1);
    this.highlighted = true;
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
  var xaxis = this.flot.getAxes().xaxis;
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

Plot.prototype.onHover = function(item, pos) {
  if ((!item || item !== this.hoveredItem) && !this.tooltip.isZoomed()) {
    if (item) {
      this.hideHighlight();
      // Tooltip Content
      this.tooltip.empty();
      var rev = item.series.buildinfo[item.dataIndex]['revision'].slice(0,12);
      var date = new Date(item.datapoint[0] * 1000).toDateString();
      
      // Label
      this.tooltip.append($.new('h3').text(item.series['label']));
      // Build link / time
      this.tooltip.append($.new('p').append($.new('p').text(formatBytes(item.datapoint[1])))
                      .append($.new('b').text('build '))
                      .append($.new('a')
                              .attr('href', "http://hg.mozilla.org/mozilla-central/rev/" + rev)
                              .text(rev))
                      .append($.new('span').text(' @ ' + date)));
      
      // Tooltips move relative to the plot, not the page
      var offset = this.obj.offset();
      this.tooltip.hover(item.pageX - offset.left, item.pageY - offset.top, this.hoveredItem ? true : false);
    }
    else {
      if (this.hoveredItem)
        this.tooltip.unHover();
      // Move hover highlight for zooming
      var left = pos.pageX - this.flot.offset().left + this.flot.getPlotOffset().left;
      this.showHighlight(left, 400);
    }
    this.hoveredItem = item;
  }
}

$(function () {
  // Load graph data
  $.ajax({
    url: './data/series.json',
    success: function (data) {
      gGraphData = data;
      $('#graphs h3').remove();
      for (var graphname in gSeries) {
        $.new('h2').addClass('graph-header').text(graphname).appendTo($('#graphs'));
        new Plot(gSeries[graphname]);
      }
    },
    error: function(xhr, status, error) {
      $('#graphs h3').text("An error occured while loading the graph data");
      $('#graphs').append($.new('p', null, { color: '#F55' }).text(status + ': ' + error));
    },
    dataType: 'json'
  });
  
  // Close zoomed tooltips upon clicking outside of them
  $('body').bind('click', function(e) {
    if (!$(e.target).is('.tooltip') && !$(e.target).parents('.graph').length)
      $('.tooltip.zoomed').each(function(ind,ele) {
        $(ele).data('owner').unzoom();
      });
  });
});
