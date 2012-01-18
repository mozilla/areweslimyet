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
 * The Original Code is Mozmill Test code.
 *
 * The Initial Developer of the Original Code is the Mozilla Foundation.
 * Portions created by the Initial Developer are Copyright (C) 2011
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
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

// Include required modules
//var addons = require("addons");
//var graphics = require("graphics");
var performance = require("performance");

var frame = {};
Components.utils.import('resource://mozmill/modules/frame.js', frame);

/**
 * Constructor
 *
 * @constructor
 * 
 * @param {MozMillController} controller
 *        MozMillController of the window to operate on
 */
function EnduranceManager(controller) {
  this._controller = controller;
  this._perfTracer = new performance.PerfTracer("Endurance");
  this._currentIteration = 1;
  this._currentEntity = 1;
  if ("endurance" in persisted) {
    this._delay = persisted.endurance.delay;
    this._iterations = persisted.endurance.iterations;
    this._entities = persisted.endurance.entities;
  } else {
    // Running the endurance test directly so set default values
    this._delay = 100;
    this._iterations = 1;
    this._entities = 1;
  }

  /*frame.events.fireEvent('installedAddons',
    addons.getInstalledAddons(function (addon) {
      return {
        id : addon.id,
        type : addon.type,
        name : addon.name,
        version : addon.version,
        isActive : addon.isActive,
        isCompatible : addon.isCompatible
      }
    })
  );

  graphics = new graphics.Graphics();
  frame.events.fireEvent('graphics', graphics.gather());*/
}

/**
 * Endurance class
 */
EnduranceManager.prototype = {

  /**
   * Get the number of entities
   *
   * @returns {Number} Number of entities
   */
  get entities() {
    return this._entities;
  },

  /**
   * Get the current entity
   *
   * @returns {Number} Current entity
   */
  get currentEntity() {
    return this._currentEntity;
  },

  /**
   * Run endurance test
   *
   * @param {function} callback
   *        Callback function to call
   */
  run : function endurance_run(callback) {
    var _testResults = {
      testMethod : frame.events.currentTest.__name__,
      testFile : frame.events.currentModule.__file__,
      iterations : [ ]
    };

    for (var i = 0; i < this._iterations; i++) {
      this._currentIteration = i + 1;
      this._controller.sleep(this._delay);

      // Run the main test method
      callback();

      _testResults.iterations.push({"checkpoints" : this._perfTracer._log});
      this._perfTracer.clearLog();
    }
    frame.events.fireEvent('enduranceResults', _testResults)
  },

  /**
   * Loop through each of the entities
   *
   * @param {function} callback
   *        Callback function to call
   */
  loop : function endurance_loop(callback) {
    for (var i = 0; i < this._entities; i++) {
      this._currentEntity = i + 1;
      callback();
      this._controller.sleep(this._delay);
    }
  },

  /**
   * Add a checkpoint.
   *
   * @param {string} label
   *        Label for checkpoint
   * @param {function} callback
   *        Callback function to call when complete
   */
  addCheckpoint : function endurance_addCheckpoint(label, callback) {
    this._perfTracer.addCheckpoint(label +
                                   " [i:" + this._currentIteration +
                                   " e:" + this._currentEntity + "]", callback);
  }

}

// Export of classes
exports.EnduranceManager = EnduranceManager;
