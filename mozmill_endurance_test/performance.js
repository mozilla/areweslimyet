/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is MozMill Test code.
 *
 * The Initial Developer of the Original Code is the Mozilla Foundation.
 * Portions created by the Initial Developer are Copyright (C) 2010
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *   Geo Mealer <gmealer@mozilla.com>
 *   Dave Hunt <dhunt@mozilla.com>
 *
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 *
 * ***** END LICENSE BLOCK ***** */

var memMgr = Cc["@mozilla.org/memory-reporter-manager;1"].
             getService(Ci.nsIMemoryReporterManager);

/**
 * PERFORMANCE TRACER
 *
 * Keeps a trace log of both actions and performance statistics
 * throughout a test run.
 *
 * Performance stats currently include explicit and resident memory.
 * More stats will be added as methods to read them are discovered.
 *
 * Usage:
 *   Before test, create a new PerfTracer named after the test.
 *     Ex: var perf = new performance.PerfTracer("MyTestFunc");
 *
 *   During test, after notable actions call PerfTracer.addCheckpoint(label)
 *     Ex: perf.addCheckpoint("Opened preferences dialog");
 *
 *   After test, call PerfTracer.finish()
 *     Ex: perf.finish();
 */

/**
 * PerfTracer constructor
 *
 * @param {string} name
 *        Name of the tracer, currently used in the output title
 */
function PerfTracer(name) {
  if (!name) {
    throw new Error(arguments.callee.name + ": name not supplied.");
  }

  this.clearLog();
  this._name = name;
}

// HACK to get resident data on old linux builds for AWSY data
function _tryGetLinuxResident() {
  try {
    var file = Components.classes["@mozilla.org/file/local;1"]
              .createInstance(Components.interfaces.nsILocalFile);
    file.initWithPath("/proc/self/statm");
    var istream = Components.classes["@mozilla.org/network/file-input-stream;1"]
                  .createInstance(Components.interfaces.nsIFileInputStream);
    istream.init(file, 0x01, 0444, 0);
    istream instanceof Components.interfaces.nsILineInputStream;
    var line = {};
    istream.readLine(line);
    istream.close();
    // Second field in /proc/self/statm is resident pages
    // HACK again! Pagesize might not be 4096.
    var ret = line.value.split(' ')[1] * 4096;
    return ret ? ret : null;
  } catch (e) {
    return null;
  }
}

PerfTracer.prototype = {
  // PUBLIC INTERFACE

  /**
   * Clears the tracker log and starts over
   */
  clearLog : function PerfTracer_clearLog() {
    this._log = new Array();
  },

  /**
   * Adds a checkpoint to the tracker log, with time and performance info.
   *
   * @param {string} aLabel
   *        Label attached to performance results. Typically should be
   *        whatever the test just did.
   *
   * @param {function} aCallback
   *        Callback to call when this checkpoint finishes (the memory reporters
   *        do not return immediately)
   */
  addCheckpoint : function PerfTracer_addCheckpoint(aLabel) {
    var result = {
      label : aLabel,
      timestamp : new Date(),
      memory : {}
    };

    // These *should* be identical to the explicit/resident root node
    // sum, AND the explicit/resident node explicit value (on newer builds),
    // but we record all three so we can make sure the data is consistent
    result['memory']['manager_explicit'] = memMgr.explicit;
    result['memory']['manager_resident'] = memMgr.resident;

    var knownHeap = 0;

    function addReport(path, amount, kind, units) {
      // Harness assumes a default of bytes to not bloat output (99% of
      // reporters are bytes)
      var unitname;
      switch (units) {
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
      if (result['memory'][path]) {
        if (unitname)
          result['memory'][path]['val'] += amount;
        else
          result['memory'][path] += amount;
      } else if (unitname) {
        result['memory'][path] = { 'unit': unitname, 'val': amount };
      } else {
        result['memory'][path] = amount;
      }

      if (kind !== undefined && kind == Ci.nsIMemoryReporter.KIND_HEAP
          && path.indexOf('explicit/') == 0)
        knownHeap += amount;
    }

    // Callback for new-style multireporters
    function reportCallback(proc, path, kind, units, amount, description,
                            closure) {
      addReport(path, amount, kind, units);
    }

    // Normal reporters
    var normal_is_multi = false;
    if (memMgr.getReportsForThisProcess) {
      // After bug 947802, this call gets all the reports we need
      // Bug 1010064 added anonymize as a necessary argument, but extra
      // arguments are ignored in builds before this
      memMgr.getReportsForThisProcess(reportCallback, null,
                                      /* anonymize */ false);
    } else {
      // Prior to bug 947802, we had to get all reporters and call getreports on
      // each one
      var reporters = memMgr.enumerateReporters();
      while (reporters.hasMoreElements()) {
        var r = reporters.getNext();
        r instanceof Ci.nsIMemoryReporter;
        if (r.collectReports) {
          // Bug 910517 removed old-style reporters and renamed
          // nsIMemoryMultiReporter to nsIMemoryReporter.
          // Fall through to handle all reporters as multi-reporters.
          normal_is_multi = true;
          break;
        }
        // Old style reporters simply had values to query, pass those
        // to addReport
        if (r.path.length) {
          // memoryUsed was renamed to amount in gecko7
          var amount = (r.amount !== undefined) ? r.amount : r.memoryUsed;
          addReport(r.path, amount, r.kind, r.units);
        }
      }

      // Multi-reporters, which take a callback.
      if (normal_is_multi || memMgr.enumerateMultiReporters) {
        var multireporters = normal_is_multi ? memMgr.enumerateReporters()
          : memMgr.enumerateMultiReporters();

        while (multireporters.hasMoreElements()) {
          var mr = multireporters.getNext();
          mr instanceof (normal_is_multi ? Ci.nsIMemoryReporter : Ci.nsIMemoryMultiReporter);
          mr.collectReports(reportCallback, null);
        }
      }
    }

    var heapAllocated = result['memory']['heap-allocated'];
    // Called heap-used in older builds
    if (!heapAllocated) heapAllocated = result['memory']['heap-used'];
    // This is how about:memory calculates derived value heap-unclassified, which
    // is necessary to get a proper explicit value.
    if (knownHeap && heapAllocated)
      result['memory']['explicit/heap-unclassified'] = result['memory']['heap-allocated'] - knownHeap;

    // If the build doesn't have a resident/explicit reporter, but does have
    // the memMgr.explicit/resident field, use that
    if (!result['memory']['resident'])
      result['memory']['resident'] = result['memory']['manager_resident']
    if (!result['memory']['explicit'])
      result['memory']['explicit'] = result['memory']['manager_explicit']

    // Linux only HACK for getting old resident data on AWSY
    if (!result['memory']['resident']) {
      result['memory']['resident'] = _tryGetLinuxResident();
    }

    this._log.push(result);
  },
}

// Exported class
exports.PerfTracer = PerfTracer;
