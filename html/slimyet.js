
"use strict";

jQuery.new = function(e, attrs, css) {
  var ret = jQuery(document.createElement(e));
  if (attrs) ret.attr(attrs);
  if (css) ret.css(css);
  return ret;
};

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
  }
};

var gZoomedGraph;
var gGraphData;
var gPerBuildData = {};

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

function treeExpandNode(node, noanimate) {
  var subtree = node.find('.subtree');
  if (!subtree.length) {
    var subtree = $.new('div').addClass('subtree').hide();
    renderMemoryTree(subtree, node.data('nodeData'), node.data('select'), node.data('memNode'));
    subtree.appendTo(node);
  }
  if (noanimate)
    subtree.show();
  else
    subtree.slideDown();
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

function renderMemoryTree(target, data, select, memNode) {
  var i = 0;
  
  function defval(obj) {
    return obj['_val'] !== undefined ? obj['_val'] : obj['_sum'] !== undefined ? obj['_sum'] : null;
  }
  
  // Sort nodes
  var rows = [];
  for (var node in data) {
    if (node == '_val' || node == '_sum')
      continue;
    window.console.log("Pushing "+node);
    rows.push(node);
  }
  if (memNode) {
    // Sort by memory size
    rows.sort(function (a, b) {
      var av = defval(data[a]) == null ? 0 : defval(data[a]);
      var bv = defval(data[b]) == null ? 0 : defval(data[b]);
      return bv - av;
    });
  } else {
    // Sort alphanumeric
    rows = rows.sort();
  }
  
  // Add rows
  var parentval = defval(data);
  for (var row = 0; row < rows.length; row++) {
    var node = rows[row];
    // Return to event loop every 50 items
    // (in conjunction with delete data[node] below)
    if (i++ > 50) {
      window.setTimeout(function() { renderMemoryTree(target, data, select, memNode); }, 0);
      return;
    }
    
    var treeNode = $.new('div')
                    .addClass('treeNode')
                    .data('nodeData', data[node])
                    .data('memNode', (memNode || node == 'mem'));
    var nodeTitle = $.new('div')
                     .addClass('treeNodeTitle')
                     .appendTo(treeNode);

    // Add value if inside a memNode
    var val = defval(data[node]);
    if (memNode && val != null) {
      // Value
      $.new('div').addClass('treeValue')
                  .text(formatBytes(val))
                  .appendTo(nodeTitle);
      // Percentage
      var pct = "("+prettyFloat(val / parentval)+"%)";
      if (parentval != null) {
        $.new('div').addClass('treeValuePct')
                    .text(pct)
                    .appendTo(nodeTitle);
      }
    }
    
    // Add label
    $.new('span').addClass('treeNodeLabel').appendTo(nodeTitle).text(node);

    // Add treeExpandClicker and click handler if node has children
    var expandClick = $.new('div').addClass('treeExpandClicker');
    nodeTitle.prepend(expandClick);
    for (var x in data[node]) {
      if (x !== '_val' && x !== '_sum') {
        expandClick.text('[+]');
        nodeTitle.click(function () { treeToggleNode($(this).parent()); });
        break;
      }
    }
    
    delete data[node];
    target.append(treeNode);
  }
}

//
// Tooltip stuff
//

function tooltipHover(tooltip, x, y, nofade) {
  if (tooltip.is('.zoomed'))
    return;
  
  if (x === undefined || y === undefined)
  {
    tooltip.stop().fadeTo(200, 0, function () { $(this).hide(); });
    return;
  }
  
  var poffset = tooltip.parent().offset();
  
  var h = tooltip.outerHeight();
  var w = tooltip.outerWidth();
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
  
  tooltip.css({
    top: top,
    left: left
  });
  
  // Show tooltip
  if (!nofade)
    tooltip.stop().fadeTo(200, 1);
}

function tooltipZoom(tooltip) {
  var w = tooltip.parent().width();
  var h = tooltip.parent().height();
    
  tooltip.show();
  tooltip.stop().addClass('zoomed').animate({
    width: '110%',
    height: '100%',
    left: '-5%',
    top: '-5%',
    opacity: 1
  }, 500);
}

function tooltipUnZoom(tooltip) {
  if (tooltip.is('.zoomed') && !tooltip.is(':animated'))
  {
    tooltip.animate({
        width: '50%',
        height: '50%',
        top: '25%',
        left: '25%',
        opacity: '0'
      }, 250, function() {
        tooltip.removeAttr('style').hide().removeClass('zoomed');
    });
    
    // onUnZoom callback
    var callback = tooltip.data('onUnZoom');
    if (callback instanceof Function)
      callback.apply(tooltip);
    tooltip.data('onUnZoom', null);
  }
}

//
// Ajax for getting more graph data
//

function getPerBuildData(buildname, success, fail) {
  if (gPerBuildData[buildname]) {
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

function PlotClick(plot, item) {
  if (item) {
    var tooltip = plot.find('.tooltip');
    tooltipZoom(tooltip);
    // Attach everything to an abs div so it can fade out without
    // affecting flow
    var fadeOut = $.new('div', null, { position: 'absolute' })
                    .append(tooltip.children())
                    .appendTo(tooltip)
                    .fadeTo(500, 0, function () {
                      $(this).remove();
                    });
    var loading = $.new('h2', null, {
      display: 'none',
      'text-align': 'center',
      'margin-top': '200px'
    }).text('Loading datapoint...')
      .appendTo(tooltip)
      .fadeIn();
      
    // Load per build data
    var canceled = false;
    var revision = gGraphData['builds'][item.dataIndex]['revision'];
    getPerBuildData(revision, function () {
      // On get data (can be immediate)
      if (!canceled)
      {
        // FIXME add header
        var series_info = gGraphData['series_info'][item.series.name];
        var nodes = gPerBuildData[revision][series_info['test']]['nodes'];
        var subnode = series_info['datapoint'].split('/');
        
        tooltip.empty();
        $.new('h2').text(series_info['test']).appendTo(tooltip);
        $.new('h3').text(series_info['datapoint']).appendTo(tooltip);
        
        renderMemoryTree(tooltip, nodes, series_info['datapoint']);
      }
    }, function (error) {
      // On failure
      loading.text("An error occured while loading the datapoint");
      tooltip.append($.new('p', null, { color: '#F55' }).text(status + ': ' + error));
    });
    // Cancel loading if tooltip is closed before the callback
    tooltip.data('onUnZoom', function () { canceled = true; });
  }
}

function PlotHover(plot, item) {
  var tooltip = plot.find('.tooltip');
  if (item !== plot.data('hoveredItem') && !tooltip.is('.zoomed')) {
    if (item) {
      // Tooltip Content
      var t = tooltip.empty();
      $.new('h2').text("Nightly").appendTo(t); // FIXME
      $.new('p').text(item.series['label']).appendTo(t);
      $.new('p').text(new Date(item.datapoint[0] * 1000).toDateString()).appendTo(t);
      $.new('p').text(formatBytes(item.datapoint[1])).appendTo(t);
      $.new('p').text(gGraphData['builds'][item.dataIndex]['revision'].slice(0,12)).appendTo(t);
      
      // Tooltips move relative to the plot, not the page
      var offset = plot.offset();
      tooltipHover(tooltip, item.pageX - offset.left, item.pageY - offset.top, plot.data('hoveredItem') ? true : false);
    }
    else {
      tooltipHover(tooltip);
    }
    plot.data('hoveredItem', item);
  }
}

//
// Append a graph to #graphs
// - axis -> { 'AxisName' : 'Nicename', ... }
//
function addGraph(axis) {
  
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
  
  var plotbox = $.new('div').addClass('graph').appendTo($('#graphs'));
  var plot = $.plot(plotbox,
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
        position: 'sw',
        backgroundOpacity: 0.4
      }
    }
  );
  
  plotbox.data({ 'plot_obj' : plot });
  //
  // Graph Tooltip
  //

  plotbox.append($.new('div', { 'class' : 'tooltip' }, { 'display' : 'none' }));
  plotbox.bind("plotclick", function(event, pos, item) { PlotClick(plotbox, item); });
  plotbox.bind("plothover", function(event, pos, item) { PlotHover(plotbox, item); });
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
        addGraph(gSeries[graphname]);
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
    if (!$(e.target).is('.tooltip') && !$(e.target).parents('.tooltip').length)
      $('.tooltip.zoomed').each(function(ind,ele) {
        tooltipUnZoom($(ele));
      });
  });
});
