
/*
 * Copyright © 2012 Mozilla Corporation
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/.
 */

function updateStatus(data) {
  $('#status').empty();
  $('#status').text(data.pending.length);
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