# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import time
import os
import sys

from marionette import MarionetteTestCase
from marionette_driver import Actions
from marionette_driver.errors import JavascriptException, ScriptTimeoutException
import mozlog.structured
from marionette_driver.keys import Keys

# Talos TP5
TEST_SITES = [
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
]

# Maximum number of tabs to open
MAX_TABS = 30

# Default amount of seconds to wait in between opening tabs
PER_TAB_PAUSE = 10

# Default amount of seconds to wait for things to be settled down
SETTLE_WAIT_TIME = 30

# Amount of times to run through the test suite
ITERATIONS = 5


class TestMemoryUsage(MarionetteTestCase):
    """Provides a test that collects memory usage at various checkpoints:
      - "Start" - Just after startup
      - "StartSettled" - After an additional wait time
      - "TabsOpen" - After opening all provided URLs
      - "TabsOpenSettled" - After an additional wait time
      - "TabsOpenForceGC" - After forcibly invoking garbage collection
      - "TabsClosed" - After closing all tabs
      - "TabsClosedSettled" - After an additional wait time
      - "TabsClosedForceGC" - After forcibly invoking garbage collection
    """

    def setUp(self):
        MarionetteTestCase.setUp(self)

        self.marionette.set_context('chrome')
        self.logger = mozlog.structured.structuredlog.get_default_logger()

        self._urls = self.testvars.get("urls", TEST_SITES)
        self._pages_to_load = self.testvars.get("entities", len(self._urls))
        self._iterations = self.testvars.get("iterations", ITERATIONS)
        self._perTabPause = self.testvars.get("perTabPause", PER_TAB_PAUSE)
        self._settleWaitTime = self.testvars.get(
            "settleWaitTime", SETTLE_WAIT_TIME)
        self._maxTabs = self.testvars.get("maxTabs", MAX_TABS)

        # workaround for https://bugzilla.mozilla.org/show_bug.cgi?id=1128773
        js = os.path.abspath(os.path.join(
            __file__, os.path.pardir, "checkpoint.js"))
        with open(js) as f:
            self._checkpoint_script = f.read()

        self.reset_state()

    def tearDown(self):
        self.logger.debug("tearing down!")
        MarionetteTestCase.tearDown(self)
        self.logger.debug("done tearing down!")

    def reset_state(self):
        self._pages_loaded = 0

        # Close all tabs except one
        for x in range(len(self.marionette.window_handles) - 1):
            self.logger.debug("closing window")
            self.marionette.execute_script("gBrowser.removeCurrentTab();")
            time.sleep(0.25)

        self._tabs = self.marionette.window_handles
        self.marionette.switch_to_window(self._tabs[0])

    def do_full_gc(self):
        """Performs a full garbage collection cycle and returns when it is finished.

        Returns True on success and False on failure.
        """
        # NB: we could do this w/ a signal or the fifo queue too
        self.logger.info("starting gc...")
        gc_script = """
            const Cu = Components.utils;
            const Cc = Components.classes;
            const Ci = Components.interfaces;

            Cu.import("resource://gre/modules/Services.jsm");
            Services.obs.notifyObservers(null, "child-mmu-request", null);

            let memMgrSvc = Cc["@mozilla.org/memory-reporter-manager;1"].getService(Ci.nsIMemoryReporterManager);
            memMgrSvc.minimizeMemoryUsage(() => marionetteScriptFinished("gc done!"));
            """
        result = None
        try:
            result = self.marionette.execute_async_script(
                gc_script, script_timeout=180000)
        except JavascriptException, e:
            self.logger.error("GC JavaScript error: %s" % e)
        except ScriptTimeoutException:
            self.logger.error("GC timed out")
        except:
            self.logger.error("Unexpected error: %s" % sys.exc_info()[0])
        else:
            self.logger.info(result)

        return result is not None

    def do_memory_report(self, checkpointName):
        """Creates a memory report for all processes and and returns the
        checkpoint.

        This will block until all reports are retrieved or a timeout occurs.
        Returns the checkpoint or None on error.

        :param checkpointName: The name of the checkpoint.
        """
        self.logger.info("starting checkpoint %s..." % checkpointName)

        script = self._checkpoint_script + """
          createCheckpoint("%s");
          """ % checkpointName

        checkpoint = None
        try:
            checkpoint = self.marionette.execute_async_script(
                script, script_timeout=60000)
        except JavascriptException, e:
            self.logger.error("Checkpoint JavaScript error: %s" % e)
        except ScriptTimeoutException:
            self.logger.error("Memory report timed out")
        except:
            self.logger.error("Unexpected error: %s" % sys.exc_info()[0])
        else:
            self.logger.info("checkpoint created!")

        return checkpoint

    def open_and_focus(self):
        """Opens the next URL in the list and focuses on the tab it is opened in.

        A new tab will be opened if |_maxTabs| has not been exceeded, otherwise
        the URL will be loaded in the next tab.
        """
        page_to_load = self._urls[self._pages_loaded % len(self._urls)]
        tabs_loaded = len(self._tabs)
        is_new_tab = False

        if tabs_loaded < self._maxTabs and tabs_loaded <= self._pages_loaded:
            full_tab_list = self.marionette.window_handles

            # Trigger opening a new tab by finding the new tab button and
            # clicking it
            newtab_button = (self.marionette.find_element('id', 'tabbrowser-tabs')
                                            .find_element('anon attribute',
                                                          {'anonid': 'tabs-newtab-button'}))
            newtab_button.click()

            self.wait_for_condition(lambda mn: len(
                mn.window_handles) == tabs_loaded + 1)

            # NB: The tab list isn't sorted, so we do a set diff to determine
            #     which is the new tab
            new_tab_list = self.marionette.window_handles
            new_tabs = list(set(new_tab_list) - set(full_tab_list))

            self._tabs.append(new_tabs[0])
            tabs_loaded += 1

            is_new_tab = True

        tab_idx = self._pages_loaded % self._maxTabs

        tab = self._tabs[tab_idx]

        # Tell marionette which tab we're on
        # NB: As a work-around for an e10s marionette bug, only select the tab
        #     if we're really switching tabs.
        if tabs_loaded > 1:
            self.logger.debug("switching to tab")
            self.marionette.switch_to_window(tab)
            self.logger.debug("switched to tab")

        with self.marionette.using_context('content'):
            self.logger.info("loading %s" % page_to_load)
            self.marionette.navigate(page_to_load)
            self.logger.debug("loaded!")

        # On e10s the tab handle can change after actually loading content
        if is_new_tab:
            # First build a set up w/o the current tab
            old_tabs = set(self._tabs)
            old_tabs.remove(tab)
            # Perform a set diff to get the (possibly) new handle
            [new_tab] = set(self.marionette.window_handles) - old_tabs
            # Update the tab list at the current index to preserve the tab
            # ordering
            self._tabs[tab_idx] = new_tab

        # give the page time to settle
        time.sleep(self._perTabPause)

        self._pages_loaded += 1

    def signal_user_active(self):
        """Signal to the browser that the user is active.

        Normally when being driven by marionette the browser thinks the
        user is inactive the whole time because user activity is
        detected by looking at key and mouse events.

        This would be a problem for this test because user inactivity is
        used to schedule some GCs (in particular shrinking GCs), so it
        would make this unrepresentative of real use.

        Instead we manually cause some inconsequential activity (a press
        and release of the shift key) to make the browser think the user
        is active.  Then when we sleep to allow things to settle the
        browser will see the user as becoming inactive and trigger
        appropriate GCs, as would have happened in real use.
        """
        action = Actions(self.marionette)
        action.key_down(Keys.SHIFT)
        action.key_up(Keys.SHIFT)
        action.perform()

    def test_open_tabs(self):
        """Marionette test entry that returns an array of checkoint arrays.

        This will generate a set of checkpoints for each iteration requested.
        Upon succesful completion the results will be stored in
        |self.testvars["results"]| and accessible to the test runner via the
        |testvars| object it passed in.
        """
        # setup the results array
        results = [[] for x in range(self._iterations)]

        def create_checkpoint(name, iteration):
            checkpoint = self.do_memory_report(name)
            self.assertIsNotNone(checkpoint, "Checkpoint was recorded")
            results[iteration].append(checkpoint)

        # The first iteration gets Start and StartSettled entries before
        # opening tabs
        create_checkpoint("Start", 0)
        time.sleep(self._settleWaitTime)
        create_checkpoint("StartSettled", 0)

        for itr in range(self._iterations):
            for x in range(self._pages_to_load):
                self.open_and_focus()
                self.signal_user_active()

            create_checkpoint("TabsOpen", itr)
            time.sleep(self._settleWaitTime)
            create_checkpoint("TabsOpenSettled", itr)
            self.assertTrue(self.do_full_gc())
            create_checkpoint("TabsOpenForceGC", itr)

            # Close all tabs
            self.reset_state()

            self.logger.debug("switching to first window")
            self.marionette.switch_to_window(self._tabs[0])
            self.logger.debug("switched to first window")
            with self.marionette.using_context('content'):
                self.logger.info("navigating to about:blank")
                self.marionette.navigate("about:blank")
                self.logger.debug("navigated to about:blank")
            self.signal_user_active()

            create_checkpoint("TabsClosed", itr)
            time.sleep(self._settleWaitTime)
            create_checkpoint("TabsClosedSettled", itr)
            self.assertTrue(self.do_full_gc(), "GC ran")
            create_checkpoint("TabsClosedForceGC", itr)

        # TODO(ER): Temporary hack until bug 1121139 lands
        self.logger.info("setting results")
        self.testvars["results"] = results
