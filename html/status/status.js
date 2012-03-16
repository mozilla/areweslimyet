
/*
 * Copyright © 2012 Mozilla Corporation
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/.
 */

"use strict";

// Types in status.json
var gStatusTypes = {
  "running" : { label: "Running tests", mode: "eta" },
  "building" : { label: "Building", single: true },
  "prepared" : { label: "In run queue" },
  "completed" : { label: "Recently completed", mode: "note" },
  "failed" : { label: "Recently failed", mode: "note" },
  "pending" : { label: "Pending" },
  "skipped" : { label: "Recently skipped", mode: "note" },
}

var gStatusTables = {};
var gStartTime;

function logMsg(msg) {
  if (window.console && window.console.log)
    window.console.log(msg);
}

function logErr(msg) {
  if (window.console && window.console.error)
    window.console.error(msg);
  else
    logMsg("ERROR: " + msg);
}

function logWarn(msg) {
  if (window.console && window.console.warn)
    window.console.error(msg);
  else
    logMsg("ERROR: " + msg);
}

// Average test duration in minutes
// for estimates on this page
var gTestTime = 108;

jQuery.new = function(e, attrs, css) {
  var ret = jQuery(document.createElement(e));
  if (attrs) ret.attr(attrs);
  if (css) ret.css(css);
  return ret;
};

function htmlSanitize(str) {
  return str.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, "<br />\n");
}

function prettyEta(started) {
  var seconds = (started + gTestTime * 60) - (Date.now() / 1000);
  seconds = +seconds;
  if (seconds < 60) return "any moment";
  var minutes = Math.floor(seconds / 60);
  var hours = Math.floor(minutes / 60);
  var ret = "";
  if (hours)
    ret += (hours + "h");
  if (minutes % 60)
    ret += (ret.length ? ", " : "") + (minutes % 60) + "m";
  //if (!ret.length || seconds % 60)
  //  ret += (ret.length ? ", " : "") + Math.round(seconds % 60) + "s";
  return "~ " + ret;
}

function statusTable(name, rows, mode) {
  var ret, table, titleRow, olddata;
  if (gStatusTables[name]) {
    // Existing table
    ret = gStatusTables[name]['obj'];
    table = ret.find('.statusTable');
    olddata = gStatusTables[name]['olddata'];
    gStatusTables[name]['olddata'] = rows;
  } else {
    // New table
    var ret = $.new('div', { class: 'statusTableBox' });
    var title = $.new('h2').text(name)
                 .append($.new('span', { class: 'small' }));
    ret.append(title);
    gStatusTables[name] = { obj: ret, olddata: rows };
    var table = $.new('div', { class: 'statusTable' }).appendTo(ret);
    var titleRow = $.new('div', { class: 'statusRow title' }).appendTo(table);
    if (mode == "batches") {
      cell(titleRow, 'requested');
      cell(titleRow, 'command');
      cell(titleRow, 'note');
    } else {
      cell(titleRow, 'type');
      cell(titleRow, 'revision');
      cell(titleRow, 'build timestamp');
      if (mode == "eta") cell(titleRow, 'estimated end');
      else if (mode == "note") cell(titleRow, 'note');
    }
  }

  function cell(row, content) {
    var ret = $.new('div', { class: 'statusCell' });
    if (content) ret.html(content);
    return ret.appendTo(row);
  }

  function makeRow(data) {
    var row = $.new('div', { class: 'statusRow' });
    if (mode == "batches") {
      cell(row, (new Date(+data['requested'] * 1000)).toString());
      cell(row, JSON.stringify(data['args']));
      cell(row, htmlSanitize(data['note']));
    } else {
      var type = data['type'].charAt(0).toUpperCase() + data['type'].slice(1);
      var time = (new Date(data['timestamp']*1000)).toString();

      cell(row, type);
      if (data['revision']) {
        var link = "https://hg.mozilla.org/mozilla-central/rev/" + data['revision'].slice(0, 12);
        cell(row).append($.new('a', { href: link }).text(data['revision']));
      } else {
        cell(row, '<i class="small">none</i>');
      }
        
      cell(row, time);
      if (mode == "eta")
        cell(row, prettyEta(data['started']));
      else if (mode == "note")
        cell(row, data['note'] ? htmlSanitize(data['note']) : '<i class="small">none</i>');
    }
    return row;
  }

  if (olddata) {
    // Only add/remove the neccessary rows, using the uid given in status.json
    var newind = 0;
    var oldind = 0;
    var jrows = table.find('.statusRow').not('.dying, .title');
    if (jrows.length != olddata.length)
      logErr("Consistency error - jrows != olddata");
    while (newind < rows.length) {
      if (oldind < olddata.length && olddata[oldind]['uid'] != rows[newind]['uid']) {
        // Rows don't match, delete remainder
        for (; oldind < olddata.length; oldind++) {
          $(jrows[oldind]).remove();
        }
      }
      if (oldind < olddata.length) {
        // Found row, update ETA/note
        if (mode == "eta") {
          var update = $(jrows[oldind]).find('.statusCell:last');
          update.text(prettyEta(rows[newind]['started']));
        } else if (mode == "note" || mode == "batch") {
          var update = $(jrows[oldind]).find('.statusCell:last');
          var newnote = htmlSanitize(rows[newind].note);
          if (update.text() != newnote) { update.text(newnote); }
        }
        newind++;
        oldind++;
      } else {
        // Did not find row, insert
        var ins = makeRow(rows[newind]).appendTo(table);
        newind++;
      }
    }
    while (newind < olddata.length) {
      $(jrows[newind++]).remove();
    }
  } else {
    // new data, insert all rows, append to body
    for (var i in rows)
      table.append(makeRow(rows[i]));
    ret.appendTo($('#status'));
  }

  // Update title count
  ret.find('h2 .small').text(' {' + rows.length + '} ');
  return ret;
}

function updateStatus(data) {
  if (gStartTime != data['starttime']) {
    if (gStartTime)
      logWarn("Tester restarted, IDs of status items are not in sync. Rebuilding page.");
    gStartTime = data['starttime']
    $('#status').empty();
    gStatusTables = {};
  }
    
  var batches = [];
  batches.push.apply(batches, data['batches']);
  if (data['pendingbatches']) for (var x in data['pendingbatches']) {
    var b = $.extend({}, data['pendingbatches'][x]);
    b.note = "[Pending]" + (b.note ? " " + b.note : "");
    batches.push(b);
  }
  batches.reverse();
  statusTable('Recent batch requests', batches, 'batches');
  
  for (var x in gStatusTypes) {
    var dat = data[x];
    if (dat && gStatusTypes[x].single) dat = [ dat ];
    if (!dat) dat = [];

    statusTable(gStatusTypes[x].label, dat, gStatusTypes[x].mode);
  }

  $('#status .loading').remove();
}

function statusUpdater() {
  $.ajax({
    url: './status.json?time=' + Date.now(),
    success: function (data) {
      updateStatus(data);
    },
    dataType: 'json'
  });
}

$(function () {
  //
  // Request form
  //
  $('#reqBuildType option:first').prop('selected', true);
  $('#reqBuildType, #reqBuildMulti').change(function() {
    var val = $('#reqBuildType').val();
    var label = $('#reqStartLabel');
    var elabel = $('#reqEndLabel');
    var multi = $('#reqBuildMulti:checked').length;
    var note = $('#reqNote');
    if (val == "nightly") {
      note.text("Build the nightly for a specified date (YYYY-MM-DD)");
      if (multi) {
        label.text("First nightly");
        elabel.text("Last nightly");
      } else {
        label.text("Nightly date");
      }
    } else if (val == "tinderbox") {
      if (multi) {
        note.text("Build Tinderbox builds between two date ranges. Dates are of format \"Jan 5 2012\" or \"Jan 5 2012 4:00 pm\"");
        label.html("Builds starting at");
        elabel.text("And ending at");
      } else {
        note.html("Build an exact build available at <a href=\"ftp://ftp.mozilla.org/pub/firefox/tinderbox-builds/mozilla-central-linux64/\">ftp://ftp.mozilla.org/pub/firefox/tinderbox-builds/mozilla-central-linux64/</a>");
        label.text("Timestamp of build");
      }
    } else if (val == "compile") {
      note.text("!! Broken right now");
      if (multi) {
        label.text("First revision to build (mc-only)");
        elabel.text("Through revision");
      } else {
        label.text("Revision to build (m-c only)")
      }
    } else {
      $('#reqStartBox, #reqEndBox, #reqNote, #reqSubmitbox').hide();
      return;
    }
    
    $('#reqStartBox, #reqNote, #reqSubmitbox').show();
    if (multi) $('#reqEndBox').show();
    else $('#reqEndBox').hide();
  });

  // Submit the request
  $('#requestBuilds').submit(function () {
    if ($('#reqSubmit').prop('disabled')) return false;
    var mode = $('#reqBuildType').val();
    var start = $('#reqStartBuild').val();
    var multi = $('#reqBuildMulti:checked').length;
    var end = $('#reqEndBuild').val();
    var priority = $('#reqPriority:checked').length;

    function dParse(d) {
      var ret = +(Date.parse(d) / 1000);
      if (isNaN(ret))
        alert("Failed to parse date \"" + d + "\" with various advanced algorithms. (read: Date.parse(), and nothing else)");
      return ret;
    }
    
    if (!start.length || (multi && !end.length) || !mode) {
      alert("Fill out all the boxes. There's only two, come on!");
      return false;
    }
    if (mode == "tinderbox" && multi) {
      start = dParse(start);
      end = dParse(end);
      if (isNaN(start) || isNaN(end)) return false;
    }
    
    var args = { 'mode': mode, 'startbuild': start };
    if (multi) args['endbuild'] = end;
    if (priority) args['priority'] = 'true';

    logMsg("Submitting request " + JSON.stringify(args));

    var e = $('#reqError').removeClass('error').removeClass('success');
    e.text('submitting...');
    $('#reqSubmit').prop('disabled', true);
    
    $.ajax({
      url: './request.cgi',
      data: args,
      success: function(data) {
        $('#reqSubmit').prop('disabled', false);
        if (data['result'] == 'success') {
          e.addClass('success');
          e.text("Request succeeded. It should appear below within a few moments.");
          $('#reqStartBuild, #reqEndBuild').val('');
        } else {
          e.addClass('error');
          e.text("Error: " + data['error']);
        }
      },
      error: function() {
        $('#reqSubmit').prop('disabled', false);
        e.addClass('error');
        e.text('Unknown error occured. Try again.');
      }
    });
    return false;
  });
  // Start updates
  window.setInterval(statusUpdater, 1000);
  statusUpdater();
});