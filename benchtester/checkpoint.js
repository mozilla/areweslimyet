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
    memory: {},
  };

  var knownHeap = {};

  /**
   * Memory reporter callback.
   */
  function addReport(aProcess, aPath, aKind, aUnits, aAmount, aDescription) {
    if (!aProcess) {
      aProcess = "Main"
    }

    var unitname;
    switch (aUnits) {
      // Old builds had no units field and assumed bytes
      case undefined:
      case Ci.nsIMemoryReporter.UNITS_BYTES:
        break;
      case Ci.nsIMemoryReporter.UNITS_COUNT:
        unitname = "cnt";
        break;
      case Ci.nsIMemoryReporter.UNITS_PERCENTAGE:
        unitname = "pct";
        break;
      default:
        // Unhandled
        return;
    }

    // For types with non-bytes units the value is
    //   { 'unit': 'percent', 'val': 1234 }
    // For bytes it is just a number, so as not to bloat output (we end up
    // exporting 11k+ reporters on newer builds)
    if (!result['memory'][aProcess]) {
      result['memory'][aProcess] = {}
    }

    if (result['memory'][aProcess][aPath]) {
      if (unitname)
        result['memory'][aProcess][aPath]['val'] += aAmount;
      else
        result['memory'][aProcess][aPath] += aAmount;
    } else if (unitname) {
      result['memory'][aProcess][aPath] = { 'unit': unitname, 'val': aAmount };
    } else {
      result['memory'][aProcess][aPath] = aAmount;
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
    var keys = Object.keys(result['memory']);
    for (var idx = 0; idx < keys.length; idx++) {
      let proc = keys[idx];
      result['memory'][proc]['explicit/heap-unclassified'] = 
          result['memory'][proc]['heap-allocated'] - knownHeap[proc];
    }

    marionetteScriptFinished(result);
  }

  // Start reporting, |onFinish| is called when all process reports are received.
  var memMgr = Cc["@mozilla.org/memory-reporter-manager;1"].
      getService(Ci.nsIMemoryReporterManager);

  memMgr.getReports(addReport, null, onFinish, null, /* anonymize */ false);
}

