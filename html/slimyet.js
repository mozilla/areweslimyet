
jQuery.new = function(e, attrs, css) {
  var ret = jQuery(document.createElement(e));
  if (attrs) ret.attr(attrs);
  if (css) ret.css(css);
  return ret;
};

var gSeries = {
  'MaxMemory' : "Peak memory usage [explicit]",
  'MaxMemoryResident' : "Peak memory usage [resident]",
  'StartMemory' : "Fresh start memory [explicit]",
  'StartMemoryResident' : "Fresh start memory [resident]",
  'EndMemory' : "After test memory [explicit]",
  'EndMemoryResident' : "After test memory [resident]"
};

var gGraphData;
var gMouseoverItem;

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

//
// Tooltip stuff
//

function tooltipHover (item) {
  if ($('#tooltip').is('.zoomed'))
    return;
  if (item == gMouseoverItem)
    return;
  gMouseoverItem = item;
  
  if (item == null)
  {
    $("#tooltip").stop().fadeTo(200, 0);
    return;
  }
  
  var h = $('#tooltip').outerHeight();
  var w = $('#tooltip').outerWidth();
  // Lower-right of cursor
  var top = item.pageY + 5;
  var left = item.pageX + 5;
  // Move above cursor if too far down
  if (window.innerHeight + document.body.scrollTop < top + h + 30)
    top = item.pageY - h - 5;
  // Move left of cursor if too far right
  if (window.innerWidth + document.body.scrollLeft < left + w + 30)
    left = item.pageX - w - 5;
  
  $("#tooltip").css({
    top: top,
    left: left
  });
  
  // Show tooltip
  $("#tooltip").stop().fadeTo(200, 1);
}

function tooltipZoom () {
  var offset = $('#graphs').offset();
  var w = $('#graphs').width();
  var h =$('#graphs').height();  
    
  $('#tooltip').stop().addClass('zoomed').animate({
    width: w * 1.10,
    height: h,
    left: offset.left - w * 0.05,
    top: offset.top - h * 0.05,
    opacity: 1
  }, 500);
}

function tooltipUnZoom(event) {
  var t = $('#tooltip');
  if (t.is('.zoomed') && !t.is(':animated') && !$.contains(t.get(0), event.target))
  {
    $('#tooltip').animate({
        width: '50%',
        height: '50%',
        top: '25%',
        left: '25%',
        opacity: '0'
      }, 250, function() {
        gMouseoverItem = null;
        $('#tooltip').removeAttr('style').hide().removeClass('zoomed');
      });
  }
}

//
// Append a graph to #graphs
// - axis -> { 'AxisName' : 'Nicename', ... }
//
function addGraph(axis) {
  
  var seriesData = [];
  
  for (var x in axis) {
    seriesData.push({ label: axis[x], data: gGraphData['series'][x] });
  }
  
  var plotbox = $.new('div').addClass('graph').prependTo($('#graphs'));
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
        backgroundOpacity: 0.4
      }
    }
  );
  
  //
  // Tooltip
  //

  plotbox.bind("plotclick", function(event, pos, item) {
    if (item) {
      tooltipZoom();
      // Attach everything to an abs div so it can fade out without
      // affecting flow
      var fadeOut = $.new('div', null, { position: 'absolute' })
                     .append($('#tooltip').children())
                     .appendTo($('#tooltip'))
                     .fadeTo(500, 0, function () {
                       $(this).remove();
                     });
      $.new('h2', null, {
        display: 'none',
        'text-align': 'center',
        'margin-top': '200px'
      }).text('Loading datapoint...')
        .appendTo($('#tooltip'))
        .fadeIn();
    }
  });
  plotbox.bind("plothover", function (event, pos, item) {
    if (item && !$('#tooltip').is('.zoomed')) {
      // Tooltip Content
      var t = $('#tooltip').empty();
      $.new('h2').text("Nightly").appendTo(t); // FIXME
      $.new('p').text(seriesData[item.seriesIndex]['label']).appendTo(t);
      $.new('p').text(new Date(item.datapoint[0] * 1000).toDateString()).appendTo(t);
      $.new('p').text(formatBytes(item.datapoint[1])).appendTo(t);
      $.new('p').text(gGraphData['build_info'][item.dataIndex]['revision'].slice(0,12)).appendTo(t);
    }
    
    tooltipHover(item);
  });
}

$(function () {
  // Load graph data
  $.ajax({
    url: './data/series.json',
    success: function (data) {
      gGraphData = data;
      $('#graphs h3').remove();
      addGraph(gSeries);
    },
    error: function(xhr, status, error) {
      $('#graphs h3').text("An error occured while loading the graph data");
      $('#graphs').append($.new('p', null, { color: '#F55' }).text(status + ': ' + error));
    },
    dataType: 'json'
  });
  
  // Global handlers for tooltip
  $('body').bind('click', tooltipUnZoom);
  window.addEventListener('resize', function() {
    if ($('#tooltip').is('.zoomed'))
      tooltipZoom();
  }, false);
});
