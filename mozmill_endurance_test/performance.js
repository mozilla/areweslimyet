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
   * NOTE: The checkpoint is not added to the log immediately, but rather
   *       once all memory reporters have returned.
   *
   * @param {string} aLabel
   *        Label attached to performance results. Typically should be
   *        whatever the test just did.
   */
  addCheckpoint : function PerfTracer_addCheckpoint(aLabel) {
    var result = {
      label : aLabel,
      timestamp : new Date(),
      memory : {}
    };
    
    var knownHeap = 0;
    
    var reporters = memMgr.enumerateReporters();
    while (reporters.hasMoreElements()) {
      var r = reporters.getNext();
      r instanceof Ci.nsIMemoryReporter;
      if (r.path.length) {
        // memoryUsed was renamed to amount in gecko7
        result['memory'][r.path] = (r.amount !== undefined) ? r.amount : r.memoryUsed;
        if (r.kind == Ci.nsIMemoryReporter.KIND_HEAP)
          knownHeap += result['memory'][r.path];
      }
    }
    // Also record multireporters if they exist
    if (memMgr.enumerateMultiReporters) {
      var multireporters = memMgr.enumerateMultiReporters();
      var pendingReports = 0;
      
      if (!multireporters.hasMoreElements())
        this._log.push(result);
      
      while (multireporters.hasMoreElements()) {
        var mr = multireporters.getNext();
        mr instanceof Ci.nsIMemoryMultiReporter;
        pendingReports++;
        
        var self = this;
        mr.collectReports({ callback: function (proc, path, kind, units, amount, description, closure) {
          result['memory'][path] = amount;
          if (kind == Ci.nsIMemoryReporter.KIND_HEAP)
            knownHeap += amount;
          
          if (--pendingReports == 0) {
            // All callbacks complete
            
            var heapAllocated = result['memory']['heap-allocated'];
            // Called heap-used in older builds
            if (!heapAllocated) heapAllocated = result['memory']['heap-used'];
            
            // This is how about:memory calculates derived value heap-unclassified, which
            // is necessary to get a proper explicit value.
            if (knownHeap && heapAllocated)
              result['memory']['explicit/heap-unclassified'] = result['memory']['heap-allocated'] - knownHeap;
            
            // FIXME the result wont be pushed onto the log until all data
            // is ready. Add a callback to addCheckpoint?
            self._log.push(result);
          }
        }}, null);
      }
    } else {
      this._log.push(result);
    }
  },
}

// Exported class
exports.PerfTracer = PerfTracer;
