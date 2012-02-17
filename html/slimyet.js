
"use strict";

jQuery.new = function(e, attrs, css) {
  var ret = jQuery(document.createElement(e));
  if (attrs) ret.attr(attrs);
  if (css) ret.css(css);
  return ret;
};

// Which series from series.json to graph where with what label
var gSeries = {
  "Resident Memory" : {
    'MaxMemoryResident' : "TP5 opened in 30 tabs",
    'MaxMemoryResidentSettled' : "TP5 opened in 30 tabs [+30s]",
    'MaxMemoryResidentForceGC' : "TP5 opened in 30 tabs [+30s, forced GC]",
    'StartMemoryResident' : "Fresh start",
    'StartMemoryResidentSettled' : "Fresh start [+30s]",
    'EndMemoryResident' : "Tabs closed",
    'EndMemoryResidentSettled' : "Tabs closed [+30s]"
  },
  "Explicit Memory" : {
    'MaxMemory' : "TP5 opened in 30 tabs",
    'MaxMemorySettled' : "TP5 opened in 30 tabs [+30s]",
    'MaxMemoryForceGC' : "TP5 opened in 30 tabs [+30s, forced GC]",
    'StartMemory' : "Fresh start",
    'StartMemorySettled' : "Fresh start [+30s]",
    'EndMemory' : "Tabs closed",
    'EndMemorySettled' : "Tabs closed [+30s]"
  },
  "Possibly Interesting Things" : {
    'MaxHeapUnclassified' : "Heap Unclassified @ TP5 opened in 30 tabs [+30s]",
    'MaxJS' : "JS @ TP5 opened in 30 tabs [+30s]"
  }
};

var gZoomedGraph;
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
  
  var seriesData = [];
  
  for (var aname in axis) {
    // Build datapoint pairs from gGraphData.builds timestamps and
    // gGraphData.series[aname] values list.
    var series = [];
    for (var ind in gGraphData['series'][aname]) {
      series.push([gGraphData['builds'][ind]['time'], gGraphData['series'][aname][ind]]);
    }
    seriesData.push({ name: aname, label: axis[aname], data: series });
  }
  
  this.obj = $.new('div').addClass('graph').appendTo($('#graphs'));
  this.flot = $.plot(this.obj,
    // Data
    seriesData,
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
        tickFormatter: function(val, axis) {
          return formatBytes(val);
        }
      },
      legend: {
        backgroundColor: "#000",
        margin: 10,
        position: 'nw',
        backgroundOpacity: 0.4
      }
    }
  );
  
  //
  // Graph Tooltip
  //

  this.tooltip = new Tooltip(this.obj);
  var self = this;
  this.obj.bind("plotclick", function(event, pos, item) { self.onClick(item); });
  this.obj.bind("plothover", function(event, pos, item) { self.onHover(item); });
}

Plot.prototype.onClick = function(item) {
  if (item) {
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
    var revision = gGraphData['builds'][item.dataIndex]['revision'];
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
  }
}

Plot.prototype.onHover = function(item) {
  if (item !== this.hoveredItem && !this.tooltip.isZoomed()) {
    if (item) {
      // Tooltip Content
      this.tooltip.empty();
      var rev = gGraphData['builds'][item.dataIndex]['revision'].slice(0,12);
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
      this.tooltip.unHover();
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
        $.new('h2').text(graphname).appendTo($('#graphs'));
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
    if (!$(e.target).is('.tooltip') && !$(e.target).parents('#graphs').length)
      $('.tooltip.zoomed').each(function(ind,ele) {
        $(ele).data('owner').unzoom();
      });
  });
});
