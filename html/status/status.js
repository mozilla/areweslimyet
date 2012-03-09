
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
    
    ret.append(row);
  }
  return ret;
}

function updateStatus(data) {
  $('#status').empty();
  for (var x in gStatusTypes) {
    if (!data[x]) continue;
    var mode = x == "running" ? "eta" : null;
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
  window.setInterval(statusUpdater, 1000);
  statusUpdater();
});