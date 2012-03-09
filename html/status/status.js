
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

jQuery.new = function(e, attrs, css) {
  var ret = jQuery(document.createElement(e));
  if (attrs) ret.attr(attrs);
  if (css) ret.css(css);
  return ret;
};

function statusTable(rows) {
  var ret = $.new('div', { class: 'statusTable' });
  var titleRow = $.new('div', { class: 'statusRow title' });
  $.new('div', { class: 'statusCell' }).text('type').appendTo(titleRow);
  $.new('div', { class: 'statusCell' }).text('revision').appendTo(titleRow);
  $.new('div', { class: 'statusCell' }).text('build timestamp').appendTo(titleRow);
  ret.append(titleRow);

  for (var i in rows) {
    var build = rows[i];
    var type = build['type'].charAt(0).toUpperCase() + build['type'].slice(1);
    var link = "https://hg.mozilla.org/mozilla-central/rev/" + build['revision'].slice(0, 12);
    var time = (new Date(build['timestamp']*1000)).toString();

    var row = $.new('div', { class: 'statusRow' });
    $.new('div', { class: 'statusCell' }).text(type).appendTo(row);
    $.new('div', { class: 'statusCell' }).append($.new('a', { href: link }).text(build['revision'])).appendTo(row);
    $.new('div', { class: 'statusCell' }).text(time).appendTo(row);
    ret.append(row);
  }
  return ret;
}

function updateStatus(data) {
  $('#status').empty();
  for (var x in gStatusTypes) {
    if (!data[x]) continue;
    var title = $.new('h2').text(gStatusTypes[x])
                 .append($.new('span', { class: 'small' }).text(' {' + data[x].length + '} '));;
    $('#status').append(title)
                .append(statusTable(data[x]));
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
  window.setInterval(statusUpdater, 10000);
  statusUpdater();
});