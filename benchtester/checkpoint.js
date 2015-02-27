/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Creates a memory reporter checkpoint.
 *
 * @param {string} aLabel
 *        Label attached to the results. Typically should be
 *        whatever the test just did.
 */
function createCheckpoint(aLabel) {
  var result = {
    label: aLabel,
    timestamp: new Date(),
    reports: {},
  };

  var knownHeap = {};

  /**
   * Memory reporter callback.
   */
  function addReport(aProcess, aPath, aKind, aUnits, aAmount, aDescription) {
    if (!aProcess) {
      aProcess = "Main"
    }

    if (!result['reports'][aProcess]) {
      result['reports'][aProcess] = {}
    }

    if (result['reports'][aProcess][aPath]) {
      result['reports'][aProcess][aPath]['val'] += aAmount;
    } else {
      result['reports'][aProcess][aPath] = {
        'unit': aUnits,
        'val': aAmount,
        'kind': aKind
      };
    }

    if (aKind !== undefined && aKind == Ci.nsIMemoryReporter.KIND_HEAP
        && aPath.indexOf('explicit/') == 0) {
    
      if (!knownHeap[aProcess]) {
        knownHeap[aProcess] = 0;
      }

      knownHeap[aProcess] += aAmount;
    }
  }

  /**
   * Callback for when all processes have finished reporting.
   */
  function onFinish(aClosure) {
    // Calculate heap-unclassified for each process
    var keys = Object.keys(result['reports']);
    for (var idx = 0; idx < keys.length; idx++) {
      let proc = keys[idx];
      result['reports'][proc]['explicit/heap-unclassified'] =
          result['reports'][proc]['heap-allocated'] - knownHeap[proc];
    }

    marionetteScriptFinished(result);
  }

  // Start reporting, |onFinish| is called when all process reports are received.
  var memMgr = Cc["@mozilla.org/memory-reporter-manager;1"].
      getService(Ci.nsIMemoryReporterManager);

  // NB: |memMgr.getReports| was added in Fx28, we do not support releases
  //     prior to that.
  memMgr.getReports(addReport, null, onFinish, null, /* anonymize */ false);
}

