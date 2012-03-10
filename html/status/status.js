
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
  "running" : "Running tests",
  "preparing" : "Building",
  "queued" : "In run queue",
  "completed" : "Recently completed",
  "failed" : "Recently failed",
  "pending" : "Pending"
}

// Average test duration in minutes
// for estimates on this page
var gTestTime = 94;

jQuery.new = function(e, attrs, css) {
  var ret = jQuery(document.createElement(e));
  if (attrs) ret.attr(attrs);
  if (css) ret.css(css);
  return ret;
};

function prettyEta(seconds) {
  seconds = +seconds;
  if (seconds < 0) return "any moment";
  var minutes = Math.floor(seconds / 60);
  var hours = Math.floor(minutes / 60);
  var ret = "";
  if (hours)
    ret += (hours + "h");
  if (minutes % 60)
    ret += (ret.length ? ", " : "") + (minutes % 60) + "m";
  if (!ret.length || seconds % 60)
    ret += (ret.length ? ", " : "") + Math.round(seconds % 60) + "s";
  return "~ " + ret;
}

function statusTable(rows, mode) {
  var ret = $.new('div', { class: 'statusTable' });
  var titleRow = $.new('div', { class: 'statusRow title' });

  function cell(row, text) {
    var ret = $.new('div', { class: 'statusCell' });
    if (text) ret.text(text);
    return ret.appendTo(row);
  }
  
  cell(titleRow, 'type');
  cell(titleRow, 'revision');
  cell(titleRow, 'build timestamp');
  if (mode == "eta") cell(titleRow, 'estimated end');
  else if (mode == "note") cell(titleRow, 'note');
  ret.append(titleRow);

  for (var i in rows) {
    var build = rows[i];
    var type = build['type'].charAt(0).toUpperCase() + build['type'].slice(1);
    var link = "https://hg.mozilla.org/mozilla-central/rev/" + build['revision'].slice(0, 12);
    var time = (new Date(build['timestamp']*1000)).toString();

    var row = $.new('div', { class: 'statusRow' });
    cell(row, type);
    cell(row).append($.new('a', { href: link }).text(build['revision']));
    cell(row, time);
    if (mode == "eta")
      cell(row, prettyEta((build['started'] + gTestTime * 60) - (Date.now() / 1000)));
    else if (mode == "note")
      cell(row, build['note'] ? build['note'] : '<i class="small">none</i>');
    
    ret.append(row);
  }
  return ret;
}

function updateStatus(data) {
  $('#status').empty();
  for (var x in gStatusTypes) {
    if (!data[x]) continue;
    var mode = null;
    
    if (x == "running") mode = "eta";
    else if (x == "completed" || x == "failed") mode = "note";
    
    var title = $.new('h2').text(gStatusTypes[x])
                 .append($.new('span', { class: 'small' }).text(' {' + data[x].length + '} '));;
    $('#status').append(title)
                .append(statusTable(data[x], mode));
  }
}

function statusUpdater() {
  $.ajax({
    url: './status.json',
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
        note.text("Build Tinderbox builds between two date ranges. Dates are of format \"Jan 5th 2012\" or \"Jan 5th 2012 4:00 pm\"");
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
      if (isNaN(start) || isNaN(end)) return False;
    }
    
    var args = { 'mode': mode, 'startbuild': start };
    if (multi) args['endbuild'] = end;
    if (priority) args['priority'] = 'true';

    if (window.console && window.console.log)
      window.console.log("Submitting request " + JSON.stringify(args));

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
          e.text("Request succeeded. It may take a few minutes for it to appear here. (Note: If a build is in progress, new requests arn't parsed until it is complete.)");
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