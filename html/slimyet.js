
jQuery.new = function(e, attrs, css) {
  var ret = jQuery(document.createElement(e));
  if (attrs) ret.attr(attrs);
  if (css) ret.css(css);
  return ret;
};

//FIXME
// Async load graph data

function formatBytes(raw) {
  function prettyFloat(aFloat) {
    var ret = Math.round(aFloat * 100).toString();
    if (ret == "0") return ret;
    if (ret.length < 3)
      ret = (ret.length < 2 ? "00" : "0") + ret;
    
    var clen = (ret.length - 2) % 3;
    ret = ret.slice(0, clen) + ret.slice(clen, -2).replace(/[0-9]{3}/g, ',$&') + '.' + ret.slice(-2);
    return clen ? ret : ret.slice(1);
  }
  if (raw / 1024 < 50) {
    return prettyFloat(raw) + "B";
  } else if (raw / Math.pow(1024, 2) < 5) {
    return prettyFloat(raw / 1024) + "KiB";
  } else if (raw / Math.pow(1024, 3) < 5) {
    return prettyFloat(raw / Math.pow(1024, 2)) + "MiB";
  } else {
    return prettyFloat(raw / Math.pow(1024, 3)) + "GiB";
  }
}

function addGraph(axis) {
  var seriesData = [];
  var seriesDataPoints = [];
  
  for (var x in axis) {
    var data = gSlimGraphSeries[x];
    var datapoints = [];
    for (var i in data) {
      datapoints.push([ data[i].time, data[i].value ]);
    }
    seriesData.push(data);
    seriesDataPoints.push({ label: axis[x], data: datapoints });
  }
  
  var plotbox = $.new('div', { 'id' : 'testgraph' }, { width: '1000px', height: '500px', margin: 'auto' }).appendTo(document.body);
  var plot = $.plot(plotbox,
    // Data
    seriesDataPoints,
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
        backgroundOpacity: 0.4
      }
    }
  );
  
  //
  // Tooltip
  //
  var tooltipHovered;
  var mouseoverItem;
  var tooltip = $('#tooltip')
    .hide()
    .appendTo(document.body)
    .bind('mouseenter', function() {
        tooltipHovered = true;
      })
    .bind('mouseleave', function() {
        tooltipHovered = false;
        checkHideTooltip();
      });
    
  function checkHideTooltip() {
    window.setTimeout(function () {
      if (!mouseoverItem && !tooltipHovered && tooltip.is(':visible')) {
        tooltip.stop().fadeTo(200, 0, function () { tooltip.hide(); });
        plot.unhighlight();
      }
    }, 0);
  }
  $("#testgraph").bind("plothover", function (event, pos, item) {
    if (item == mouseoverItem)
      return;
    mouseoverItem = item;
    
    if (!item) {
      checkHideTooltip();
      return;
    }
    tooltip.css({ top: item.pageY, left: item.pageX });
    // Fill tooltip
    tooltip.find('h2').text('Nightly');
    var c = tooltip.find('p').empty();
    c.append($.new('p').text(new Date(item.datapoint[0] * 1000).toDateString()));
    c.append($.new('p').text(formatBytes(item.datapoint[1])));
    var rev = seriesData[item.seriesIndex][item.dataIndex].build.slice(0,12);
    c.append($.new('a', {
        target: '_blank',
        href: 'https://hg.mozilla.org/mozilla-central/rev/'
      }).text(rev));
    
    // Show tooltip
    plot.highlight(item.series, item.datapoint);
    tooltip.stop().fadeTo(200, 1);
  });
}

$(function () { addGraph({
    'MaxMemory' : "Peak memory usage (explicit)",
    'MaxMemoryResident' : "Peak memory usage (resident)",
    'StartMemory' : "Fresh start memory (explicit)",
    'StartMemoryResident' : "Fresh start memory (resident)",
    'EndMemory' : "After test memory (zero tabs)",
    'EndMemoryResident' : "After test memory (zero tabs) (resident)"
  });});
