/* -*- fill-column: 80; js-indent-level: 2; -*- */
/*
 * Copyright © 2014 Mozilla Corporation
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/.
 */

importScripts("zee.js");

"use strict";

// about:memory constants
var ABOUT_MEMORY_VERSION = 1;

var UNITS_BYTES = 0;
var UNITS_COUNT = 1;
var UNITS_PERCENTAGE = 3;

var KIND_NONHEAP = 0;
var KIND_HEAP = 1;
var KIND_OTHER = 2;

// Worker entry point. Serializes the checkpoint into the about:memory format
// and gzips it. A Blob containing the encoded data will be posted back to the
// caller.
onmessage = function(aEvent) {
  // oEvent.data = { filename: name, checkpoint: object }
  var reports = [];
  checkpointToAboutMemory("", aEvent.data.checkpoint, reports);

  var memoryReport = {
    version: ABOUT_MEMORY_VERSION,
    reports: reports,
    hasMozMallocUsableSize: true
  };

  var serialized = JSON.stringify(memoryReport, null, 2);
  var encoder = new TextEncoder('utf-8');
  var encoded = encoder.encode(serialized);

  var compressed = Zee.compress(encoded);

  var blob = new Blob([compressed], {type: 'application/x-gzip-compressed'});
  postMessage(blob);
}

// Converts a checkopoint entry to an about:memory compatible reports array.
// 
// @param {aPath} The node path.
// @param {aData} The data node.
// @param {aReports} The array of report entries that is being built.
function checkpointToAboutMemory(aPath, aData, aReports) {
  function defval(aObj) {
    if (typeof(aObj) == 'number') {
      return aObj;
    }
    return aObj['_val'] == undefined ? null : aObj['_val'];
  }
  
  function units(aObj) {
    if (aObj instanceof Object && '_units' in aObj) {
      var units = aObj['_units'];
      if (units == 'pct') {
        return UNITS_PERCENTAGE;
      }
      else if (units == 'cnt') {
        return UNITS_COUNT;
      }
    }

    // Default unit is bytes.
    return UNITS_BYTES;
  }

  function kind(aObj) {
    if (aObj instanceof Object && '_kind' in aObj) {
      // NB: this will need to be updated to perform a proper conversion.
      return aObj['_kind'];
    }
    else {
      // NB: If the units are bytes we just say the memory is heap memory.
      //     The distinction of heap and non-heap memory only matters for the
      //     calculation of heap-unclassified, which we already calculated.
      return units(aObj) != UNITS_BYTES ? KIND_OTHER : KIND_HEAP; 
    }
  }

  var childern = [];
  for (var node in aData) {
    // Nodes starting with _ are not children (_val, _sum, _units).
    if (node[0] != '_') {
      childern.push(node);
    }
  }

  if (childern.length == 0) {
    // This is a leaf node.
    var report = {
      description: "",
      process: "Main Process",
      amount: defval(aData),
      units: units(aData),
      path: aPath,
      kind: kind(aData)
    };
    
    aReports.push(report);
    return;
  }

  var node;
  while (node = childern.shift()) {
    var nodePath = aPath != "" ? aPath + '/' + node : node;
    checkpointToAboutMemory(nodePath, aData[node], aReports);
  }
}

