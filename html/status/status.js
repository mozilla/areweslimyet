
/*
 * Copyright © 2012 Mozilla Corporation
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/.
 */

"use strict";

// Slows down polling of status.json (it only updates every 5m on mirrors) and
// hides widgets for queuing builds (they only work on the test machine)
var gPublic = [ "areweslimyet.com", "www.areweslimyet.com" ].indexOf(document.location.hostname) != -1;

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
  return str ? str.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, "<br />\n") : str;
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
        var link = "https://hg.mozilla.org/integration/mozilla-inbound/rev/" + data['revision'].slice(0, 12);
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
        } else if (mode == "note" || mode == "batches") {
          var update = $(jrows[oldind]).find('.statusCell:last');
          var newnote = htmlSanitize(rows[newind].note);
          if (update.html() != newnote) { update.html(newnote); }
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
  if (!gPublic) {
    $('#requestBuildsNote').text('Use this responsibly! Ask in #memshrink if uncertain.');
    $('#requestBuilds').show();
    //
    // Request form
    //
    $('#reqBuildType option:first').prop('selected', true);
    $('.row,#submit,#reqNote').attr('display', null).hide();
    $('#reqBuildType, #reqBuildMulti, #reqDoSeries').change(function() {
      var val = $('#reqBuildType').val();

      if (!val) {
        $('.row,#submit,#reqNote').hide();
        return;
      }
      $('.row,#submit,#reqNote').show();

      var series = $('#reqDoSeries:checked').length;
      var multi = $('#reqBuildMulti:checked').length;

      // Ftp doesn't support multi builds, and requires a custom series.
      if ((val == "ftp" || val == "try") && multi) {
        $('#reqBuildMulti').attr('checked', false);
        multi = false;
      }
      if ((val == "ftp" || val == "try") && !series) {
        series = true;
        $('#reqDoSeries').attr('checked', true);
      }

      function showhide(sel, match) {
        val == match ? $('.'+sel).show() : $('.'+sel).hide();
        $('.'+sel + (multi ? '.single' : '.multi')).hide();
      }

      function disablebutton(ele, truefalse) {
        $('#'+ele).attr('disabled', truefalse);
        var l = $("label[for='"+ele+"']");
        truefalse ? l.addClass('disabled') : l.removeClass('disabled');
      }

      disablebutton('reqBuildMulti', val == 'try' || val == 'ftp');
      disablebutton('reqDoSeries', val == 'try' || val == 'ftp');

      showhide('modeTinderbox', "tinderbox");
      showhide('modeNightly', "nightly")
      showhide('modeCompile', "compile")
      showhide('modeFTP', "ftp")
      showhide('modeTry', "try")

      series ? $('.series').show() : $('.series').hide();
      multi ? $('#reqEndRow').show() : $('#reqEndRow').hide();
    }).change();

    // Submit the request
    $('#requestBuilds').submit(function () {
      if ($('#reqSubmit').prop('disabled')) return false;
      var mode = $('#reqBuildType').val();
      var start = $('#reqStartBuild').val();
      var multi = $('#reqBuildMulti:checked').length;
      var end = $('#reqEndBuild').val();
      var note = $('#reqMsg').val();
      var doseries = $('#reqDoSeries:checked').length;
      var series = $('#reqSeries').val();

      function dParse(d) {
        var ret;
        if (+d == d)
          ret = d
        else
          ret = Math.round(Date.parse(d) / 1000)
        if (isNaN(ret))
          alert("Failed to parse date \"" + d + "\" with various advanced algorithms. (read: Date.parse(), and nothing else)");
        return ret;
      }

      if (!start.length || (multi && !end.length) || !mode) {
        alert("Missing fields");
        return false;
      }
      if (doseries && !series.match('^[a-z0-9\-]+$')) {
        alert("Series name can only contain lowercase, numbers, and dash");
        return false;
      }
      if (mode == "tinderbox" && multi) {
        start = dParse(start);
        end = dParse(end);
        if (isNaN(start) || isNaN(end)) return false;
      }

      if (mode == "ftp") {
        start = start.replace(/^((https?)|(ftp)):\/\/ftp.mozilla.org/, "");
        start = start.replace(/^pub/, "/pub");
        if (!start.match('^/pub/')) {
          alert("The path for an FTP build should start with /pub/");
          return false;
        }
      }

      if (mode == "try") {
        if (!start.match('^[a-f0-9]+$')) {
          alert("The try changeset ID should only contain a-f, 0-9");
          return false;
        }
        // try is just a ftp build with a path of try:changeset
        start = "try:" + start;
        mode = "ftp";
      }

      var args = { 'mode': mode, 'startbuild': start };
      if (doseries) args['series'] = series;
      if (multi) args['endbuild'] = end;
      if ($('#reqDoSeries:checked').length) args['series'] = $('#reqSeries').val();
      if ($('#reqPriority:checked').length) args['prioritize'] = 'true';
      if ($('#reqForce:checked').length) args['force'] = 'true';
      if (note) args['note'] = note;

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
            $('#reqStartBuild, #reqEndBuild, #reqMsg').val('');
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
  }
  // Start updates
  // The mirror only gets updates to status.json every 5m
  window.setInterval(statusUpdater, gPublic ? 60000 : 1000);
  statusUpdater();
});
