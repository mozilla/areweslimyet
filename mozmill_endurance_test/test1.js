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
 * The Initial Developer of the Original Code is Mozilla Foundation.
 * Portions created by the Initial Developer are Copyright (C) 2011
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *   Dave Hunt <dhunt@mozilla.com> (Original Author)
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

var endurance = require("../../../../lib/endurance");
var modalDialog = require("../../../../lib/modal-dialog");
var prefs = require("../../../../lib/prefs");
var tabs = require("../../../../lib/tabs");

// Talos Standalone v2.1 Test Bundle
  // Broken - reference some external broken wikia-ads garbage
  // "http://localhost:8001/talos_pages_2.1/uncyclopedia.org_wiki_Main_Page/uncyclopedia.org/wiki/Main_Page.html",
  // "http://localhost:8001/talos_pages_2.1/uncyclopedia.org_wiki_Babel_Vi/uncyclopedia.org/wiki/BabelVi.html",
  // "http://localhost:8001/talos_pages_2.1/bioshock.wikia.com_wiki_Main_Page/bioshock.wikia.com/wiki/Main_Page.html",
  // "http://localhost:8001/talos_pages_2.1/ja.uncyclopedia.info_wiki/ja.uncyclopedia.info/wiki/index.html",
  // "http://localhost:8001/talos_pages_2.1/spademanns.wikia.com_wiki_Forside/spademanns.wikia.com/wiki/Forside.html",
  // "http://localhost:8001/talos_pages_2.1/www.wowwiki.com_Main_Page/www.wowwiki.com/Main_Page.html",
  // "http://localhost:8001/talos_pages_2.1/pushingdaisies.wikia.com_wiki_Pushing_Daisies/pushingdaisies.wikia.com/wiki/Pushing_Daisies.html",
  // Broken - ads that hang
  // "http://localhost:8001/talos_pages_2.1/en.marveldatabase.com_Main_Page/en.marveldatabase.com/Main_Page.html",

const TEST_SITES = [
  "http://localhost:8001/talos_pages_2.1/www.armchairgm.com_Main_Page/www.armchairgm.com/Main_Page.html",
  "http://localhost:8001/talos_pages_2.1/www.armchairgm.com_Anderson_Continues_to_Thrive_for_Cleveland/www.armchairgm.com/Anderson_Continues_to_Thrive_for_Cleveland.html",
  "http://localhost:8001/talos_pages_2.1/www.armchairgm.com_Special_ImageRating/www.armchairgm.com/SpecialImageRating.html",
  "http://localhost:8001/talos_pages_2.1/creativecommons.org/creativecommons.org/index.html",
  "http://localhost:8001/talos_pages_2.1/en.wikinews.org_wiki_Main_Page/en.wikinews.org/wiki/Main_Page.html",
  "http://localhost:8001/talos_pages_2.1/www.vodcars.com/www.vodcars.com/index.html",
  "http://localhost:8001/talos_pages_2.1/wikitravel.org_en_China/wikitravel.org/en/China.html",
  "http://localhost:8001/talos_pages_2.1/wikitravel.org_en_Main_Page/wikitravel.org/en/Main_Page.html",
  "http://localhost:8001/talos_pages_2.1/wikitravel.org_ja/wikitravel.org/ja/index.html",
  "http://localhost:8001/talos_pages_2.1/wikitravel.org_he/wikitravel.org/he/index.html",
  "http://localhost:8001/talos_pages_2.1/wikitravel.org_hi/wikitravel.org/hi/index.html",
  "http://localhost:8001/talos_pages_2.1/wikitravel.org_ru/wikitravel.org/ru/index.html",
  "http://localhost:8001/talos_pages_2.1/en.wikipedia.org_wiki_Main_Page/en.wikipedia.org/wiki/Main_Page.html",
  "http://localhost:8001/talos_pages_2.1/ja.wikipedia.org_wiki/ja.wikipedia.org/wiki/index.html",
  "http://localhost:8001/talos_pages_2.1/ru.wikipedia.org_wiki/ru.wikipedia.org/wiki/index.html",
  "http://localhost:8001/talos_pages_2.1/zh.wikipedia.org_wiki/zh.wikipedia.org/wiki/index.html",
  "http://localhost:8001/talos_pages_2.1/de.wikipedia.org_wiki_Hauptseite/de.wikipedia.org/wiki/Hauptseite.html",
  "http://localhost:8001/talos_pages_2.1/forums.studentdoctor.net/forums.studentdoctor.net/index.html",
  "http://localhost:8001/talos_pages_2.1/forums.studentdoctor.net_showthread/forums.studentdoctor.net/index.html",
  "http://localhost:8001/talos_pages_2.1/joi.ito.com_jp/joi.ito.com/jp/index.html",
  "http://localhost:8001/talos_pages_2.1/joi.ito.com_archives_email/joi.ito.com/archives/email/index.html"
];

const TAB_MODAL = "prompts.tab_modal.enabled";

function setupModule() {
  controller = mozmill.getBrowserController();
  enduranceManager = new endurance.EnduranceManager(controller);

  // XXX: Bug 673399
  //      Tab modal dialogs are not yet supported so we switch back to browser modal dialogss
  prefs.preferences.setPref(TAB_MODAL, false);

  md = new modalDialog.modalDialog(controller.window);
  md.start(closeModalDialog);

  tabBrowser = new tabs.tabBrowser(controller);
  tabBrowser.closeAllTabs();
}

/**
 * Run Mem Buster
 **/
function testMemBuster() {
  enduranceManager.run(function () {
    enduranceManager.loop(function () {
      var currentEntity = enduranceManager.currentEntity;

      if (tabBrowser.length < currentEntity) {
        tabBrowser.openTab();
      }

      controller.tabs.selectTabIndex(currentEntity - 1);
      controller.waitFor(function() { return controller.tabs.activeTabIndex == currentEntity - 1; });

      var siteIndex = (currentEntity - 1) % TEST_SITES.length;
      var site = TEST_SITES[siteIndex];

      controller.open(site);
    });
    
    for (var i = 0; i < tabBrowser.length; i++) {
      var tab = controller.tabs.getTab(i);
      controller.waitForPageLoad(tab, 60000, 500);
      controller.assert(function () { return tab.readyState == "complete"; });
    }
    // Settle
    controller.sleep(5000);
    enduranceManager.addCheckpoint("TabsOpen");
    tabBrowser.closeAllTabs();
    controller.waitForPageLoad(controller.tabs.activeTab);
    controller.sleep(5000);
    enduranceManager.addCheckpoint("TabsClosed");
  });
}

function closeModalDialog(controller) {
  controller.window.close();
  md.start(closeModalDialog);
}

function teardownModule() {
  md.stop();
  tabBrowser.closeAllTabs();
}
