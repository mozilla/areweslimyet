
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

function updateStatus(data) {
  $('#status').empty();
  $('#status').text('(placeholder)');
  $('#status').append($.new('pre', null,
                            {
                              'text-align': 'left',
                              'width' : '500px',
                              'margin': 'auto',
                              'background-color': '#433',
                              'padding': '15px'
                            }).text(data));
}

function statusUpdater() {
  $.ajax({
    url: './status.json',
    success: function (data) {
      updateStatus(data);
    },
    dataType: 'text'
  });
}

$(function () {
  window.setInterval(statusUpdater, 10000);
  statusUpdater();
});