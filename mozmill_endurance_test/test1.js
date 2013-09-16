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

"use strict";

var endurance = require("endurance");
var modalDialog = require("modal-dialog");
var prefs = require("prefs");
var tabs = require("tabs");

// Talos TP5
const TEST_SITES = [
  "http://localhost:8001/tp5/thesartorialist.blogspot.com/thesartorialist.blogspot.com/index.html",
  "http://localhost:8002/tp5/cakewrecks.blogspot.com/cakewrecks.blogspot.com/index.html",
  "http://localhost:8003/tp5/baidu.com/www.baidu.com/s@wd=mozilla.html",
  "http://localhost:8004/tp5/en.wikipedia.org/en.wikipedia.org/wiki/Rorschach_test.html",
  "http://localhost:8005/tp5/twitter.com/twitter.com/ICHCheezburger.html",
  "http://localhost:8006/tp5/msn.com/www.msn.com/index.html",
  "http://localhost:8007/tp5/yahoo.co.jp/www.yahoo.co.jp/index.html",
  "http://localhost:8008/tp5/amazon.com/www.amazon.com/Kindle-Wireless-Reader-Wifi-Graphite/dp/B002Y27P3M/507846.html",
  "http://localhost:8009/tp5/linkedin.com/www.linkedin.com/in/christopherblizzard@goback=.nppvan_%252Flemuelf.html",
  "http://localhost:8010/tp5/bing.com/www.bing.com/search@q=mozilla&go=&form=QBLH&qs=n&sk=&sc=8-0.html",
  "http://localhost:8011/tp5/icanhascheezburger.com/icanhascheezburger.com/index.html",
  "http://localhost:8012/tp5/yandex.ru/yandex.ru/yandsearch@text=mozilla&lr=21215.html",
  "http://localhost:8013/tp5/cgi.ebay.com/cgi.ebay.com/ALL-NEW-KINDLE-3-eBOOK-WIRELESS-READING-DEVICE-W-WIFI-/130496077314@pt=LH_DefaultDomain_0&hash=item1e622c1e02.html",
  "http://localhost:8014/tp5/163.com/www.163.com/index.html",
  "http://localhost:8015/tp5/mail.ru/mail.ru/index.html",
  "http://localhost:8016/tp5/bbc.co.uk/www.bbc.co.uk/news/index.html",
  "http://localhost:8017/tp5/store.apple.com/store.apple.com/us@mco=Nzc1MjMwNA.html",
  "http://localhost:8018/tp5/imdb.com/www.imdb.com/title/tt1099212/index.html",
  "http://localhost:8019/tp5/mozilla.com/www.mozilla.com/en-US/firefox/all-older.html",
  "http://localhost:8020/tp5/ask.com/www.ask.com/web@q=What%27s+the+difference+between+brown+and+white+eggs%253F&gc=1&qsrc=3045&o=0&l=dir.html",
  "http://localhost:8021/tp5/cnn.com/www.cnn.com/index.html",
  "http://localhost:8022/tp5/sohu.com/www.sohu.com/index.html",
  "http://localhost:8023/tp5/vkontakte.ru/vkontakte.ru/help.php@page=about.html",
  "http://localhost:8024/tp5/youku.com/www.youku.com/index.html",
  "http://localhost:8025/tp5/myparentswereawesome.tumblr.com/myparentswereawesome.tumblr.com/index.html",
  "http://localhost:8026/tp5/ifeng.com/ifeng.com/index.html",
  "http://localhost:8027/tp5/ameblo.jp/ameblo.jp/index.html",
  "http://localhost:8028/tp5/tudou.com/www.tudou.com/index.html",
  "http://localhost:8029/tp5/chemistry.about.com/chemistry.about.com/index.html",
  "http://localhost:8030/tp5/beatonna.livejournal.com/beatonna.livejournal.com/index.html",
  "http://localhost:8031/tp5/hao123.com/hao123.com/index.html",
  "http://localhost:8032/tp5/rakuten.co.jp/www.rakuten.co.jp/index.html",
  "http://localhost:8033/tp5/alibaba.com/www.alibaba.com/product-tp/101509462/World_s_Cheapest_Laptop.html",
  "http://localhost:8034/tp5/uol.com.br/www.uol.com.br/index.html",
  "http://localhost:8035/tp5/cnet.com/www.cnet.com/index.html",
  "http://localhost:8036/tp5/ehow.com/www.ehow.com/how_4575878_prevent-fire-home.html",
  "http://localhost:8037/tp5/thepiratebay.org/thepiratebay.org/top/201.html",
  "http://localhost:8038/tp5/page.renren.com/page.renren.com/index.html",
  "http://localhost:8039/tp5/chinaz.com/chinaz.com/index.html",
  "http://localhost:8040/tp5/globo.com/www.globo.com/index.html",
  "http://localhost:8041/tp5/spiegel.de/www.spiegel.de/index.html",
  "http://localhost:8042/tp5/dailymotion.com/www.dailymotion.com/us.html",
  "http://localhost:8043/tp5/goo.ne.jp/goo.ne.jp/index.html",
  "http://localhost:8044/tp5/alipay.com/www.alipay.com/index.html",
  "http://localhost:8045/tp5/stackoverflow.com/stackoverflow.com/questions/184618/what-is-the-best-comment-in-source-code-you-have-ever-encountered.html",
  "http://localhost:8046/tp5/nicovideo.jp/www.nicovideo.jp/index.html",
  "http://localhost:8047/tp5/ezinearticles.com/ezinearticles.com/index.html@Migraine-Ocular---The-Eye-Migraines&id=4684133.html",
  "http://localhost:8048/tp5/taringa.net/www.taringa.net/index.html",
  "http://localhost:8049/tp5/tmall.com/www.tmall.com/index.html@ver=2010s.html",
  "http://localhost:8050/tp5/huffingtonpost.com/www.huffingtonpost.com/index.html",
  "http://localhost:8051/tp5/deviantart.com/www.deviantart.com/index.html",
  "http://localhost:8052/tp5/media.photobucket.com/media.photobucket.com/image/funny%20gif/findstuff22/Best%20Images/Funny/funny-gif1.jpg@o=1.html",
  "http://localhost:8053/tp5/douban.com/www.douban.com/index.html",
  "http://localhost:8054/tp5/imgur.com/imgur.com/gallery/index.html",
  "http://localhost:8055/tp5/reddit.com/www.reddit.com/index.html",
  "http://localhost:8056/tp5/digg.com/digg.com/news/story/New_logo_for_Mozilla_Firefox_browser.html",
  "http://localhost:8057/tp5/filestube.com/www.filestube.com/t/the+vampire+diaries.html",
  "http://localhost:8058/tp5/dailymail.co.uk/www.dailymail.co.uk/ushome/index.html",
  "http://localhost:8059/tp5/whois.domaintools.com/whois.domaintools.com/mozilla.com.html",
  "http://localhost:8060/tp5/indiatimes.com/www.indiatimes.com/index.html",
  "http://localhost:8061/tp5/rambler.ru/www.rambler.ru/index.html",
  "http://localhost:8062/tp5/torrentz.eu/torrentz.eu/search@q=movies.html",
  "http://localhost:8063/tp5/reuters.com/www.reuters.com/index.html",
  "http://localhost:8064/tp5/foxnews.com/www.foxnews.com/index.html",
  "http://localhost:8065/tp5/xinhuanet.com/xinhuanet.com/index.html",
  "http://localhost:8066/tp5/56.com/www.56.com/index.html",
  "http://localhost:8067/tp5/bild.de/www.bild.de/index.html",
  "http://localhost:8068/tp5/guardian.co.uk/www.guardian.co.uk/index.html",
  "http://localhost:8069/tp5/w3schools.com/www.w3schools.com/html/default.asp.html",
  "http://localhost:8070/tp5/naver.com/www.naver.com/index.html",
  "http://localhost:8071/tp5/blogfa.com/blogfa.com/index.html",
  "http://localhost:8072/tp5/terra.com.br/www.terra.com.br/portal/index.html",
  "http://localhost:8073/tp5/ucoz.ru/www.ucoz.ru/index.html",
  "http://localhost:8074/tp5/yelp.com/www.yelp.com/biz/alexanders-steakhouse-cupertino.html",
  "http://localhost:8075/tp5/wsj.com/online.wsj.com/home-page.html",
  "http://localhost:8076/tp5/noimpactman.typepad.com/noimpactman.typepad.com/index.html",
  "http://localhost:8077/tp5/myspace.com/www.myspace.com/albumart.html",
  "http://localhost:8078/tp5/google.com/www.google.com/search@q=mozilla.html",
  "http://localhost:8079/tp5/orange.fr/www.orange.fr/index.html",
  "http://localhost:8080/tp5/php.net/php.net/index.html",
  "http://localhost:8081/tp5/zol.com.cn/www.zol.com.cn/index.html",
  "http://localhost:8082/tp5/mashable.com/mashable.com/index.html",
  "http://localhost:8083/tp5/etsy.com/www.etsy.com/category/geekery/videogame.html",
  "http://localhost:8084/tp5/gmx.net/www.gmx.net/index.html",
  "http://localhost:8085/tp5/csdn.net/csdn.net/index.html",
  "http://localhost:8086/tp5/xunlei.com/xunlei.com/index.html",
  "http://localhost:8087/tp5/hatena.ne.jp/www.hatena.ne.jp/index.html",
  "http://localhost:8088/tp5/icious.com/www.delicious.com/index.html",
  "http://localhost:8089/tp5/repubblica.it/www.repubblica.it/index.html",
  "http://localhost:8090/tp5/web.de/web.de/index.html",
  "http://localhost:8091/tp5/slideshare.net/www.slideshare.net/jameswillamor/lolcats-in-popular-culture-a-historical-perspective.html",
  "http://localhost:8092/tp5/telegraph.co.uk/www.telegraph.co.uk/index.html",
  "http://localhost:8093/tp5/seesaa.net/blog.seesaa.jp/index.html",
  "http://localhost:8094/tp5/wp.pl/www.wp.pl/index.html",
  "http://localhost:8095/tp5/aljazeera.net/aljazeera.net/portal.html",
  "http://localhost:8096/tp5/w3.org/www.w3.org/standards/webdesign/htmlcss.html",
  "http://localhost:8097/tp5/homeway.com.cn/www.hexun.com/index.html",
  "http://localhost:8098/tp5/facebook.com/www.facebook.com/Google.html",
  "http://localhost:8099/tp5/youtube.com/www.youtube.com/music.html",
  "http://localhost:8100/tp5/people.com.cn/people.com.cn/index.html"
];

const TAB_MODAL = "prompts.tab_modal.enabled";

const MAX_TABS = 30;

var controller;
var enduranceManager;
var tabBrowser;
var md;
var perTabPause;
var settleWaitTime;

function setupModule() {
  controller = mozmill.getBrowserController();
  enduranceManager = new endurance.EnduranceManager(controller);

  if ("endurance" in persisted) {
    perTabPause = persisted.endurance.perTabPause * 1000;
    settleWaitTime = persisted.endurance.settleWaitTime * 1000;
  }

  if (perTabPause === undefined)
    perTabPause = 10000;
  if (settleWaitTime === undefined)
    settleWaitTime = 30000;

  // XXX: Bug 673399
  //      Tab modal dialogs are not yet supported so we switch back to browser modal dialogss
  prefs.preferences.setPref(TAB_MODAL, false);

  md = new modalDialog.modalDialog(controller.window);
  md.start(closeModalDialog);

  tabBrowser = new tabs.tabBrowser(controller);
  tabBrowser.closeAllTabs();

  // Use bad proxy settings to break any non-localhost access
  //var prefs = Components.classes["@mozilla.org/preferences-service;1"]
  //                      .getService(Components.interfaces.nsIPrefService);
  //prefs = prefs.getBranch("network.proxy.");
  prefs.preferences.setPref("network.proxy.socks", "localhost");
  prefs.preferences.setPref("network.proxy.socks_port", 90000); // Invalid port
  prefs.preferences.setPref("network.proxy.socks_remote_dns", true);
  prefs.preferences.setPref("network.proxy.type", 1); // Socks

  // We're not testing flash memory usage. Also, it likes to crash in VNC sessions.
  prefs.preferences.setPref("plugin.disable", true);
}

/**
 * Run Mem Test
 **/
function testMemoryUsage() {
  function waitGC() {
    var complete = false;
    enduranceManager.doFullGC(function () {
      complete = true;
    }, 50);
    controller.waitFor(function () { return complete; }, null, 60000, 500);
  }

  var initial = true;
  enduranceManager.run(function () {
    if (initial) {
      initial = false;
      enduranceManager.addCheckpoint("Start");
      controller.sleep(settleWaitTime);
      enduranceManager.addCheckpoint("StartSettled");
    }
    enduranceManager.loop(function () {
      var currentEntity = enduranceManager.currentEntity;

      var tabNum = (currentEntity - 1) % MAX_TABS;
      if (tabBrowser.length < tabNum + 1) {
        tabBrowser.openTab();
      }

      controller.tabs.selectTabIndex(tabNum);
      controller.waitFor(function() { return controller.tabs.activeTabIndex == tabNum; }, 60000, 500);

      var siteIndex = (currentEntity - 1) % TEST_SITES.length;
      var site = TEST_SITES[siteIndex];

      controller.open(site);
      controller.waitForPageLoad(controller.tabs.activeTab, 60000, 500);
      controller.assert(function () { return controller.tabs.activeTab.readyState == "complete"; });
      controller.sleep(perTabPause);
    });

    enduranceManager.addCheckpoint("TabsOpen");
    controller.sleep(settleWaitTime);
    enduranceManager.addCheckpoint("TabsOpenSettled");
    waitGC();
    enduranceManager.addCheckpoint("TabsOpenForceGC");
    tabBrowser.closeAllTabs();
    controller.waitForPageLoad(controller.tabs.activeTab);
    enduranceManager.addCheckpoint("TabsClosed");
    controller.sleep(settleWaitTime);
    enduranceManager.addCheckpoint("TabsClosedSettled");
    waitGC();
    enduranceManager.addCheckpoint("TabsClosedForceGC");
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
