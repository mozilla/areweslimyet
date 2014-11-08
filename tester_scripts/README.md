These are the scripts the internal test box uses to automate running AWSY,
they're mostly hacky and setup for that specific environment. Useful as examples
at best.

## How to run your own areweslimyet.com clone (roughly)

- Install prerequisites (x11, Firefox deps, python, git, mercurial)
- Clone this repo, and subrepos.
- Clone mozilla-inbound to $AWSY/mozilla-inbound (used by BuildGetter)
- Install mozmill 1.5 (unless we've since ported to mozmill 2)
- Obtain a copy of the TP5 pageset
- Setup a webserver to host TP5 at localhost:8001 through localhost:8100. See
e.g. tp5.nginx.conf
- Setup a server to host areweslimyet, i.e. the html/ directory
- Setup a cron job to run create_graph_json.py and merge_graph_json.py, see
cron.sh for an example.
- mkdir $AWSY/db/, used by the default slimtest config as the database path.
- Ensure vncserver is setup, and can create sessions without interaction.
- Run the test daemon. See launch_tester.sh as an example.
- [Optional] Setup a cron job to run util/queue_tinderbox_builds.py, which
  auto-queues all tinderbox builds from mozilla-inbound with the tester as they
  show up.
- [Optional] Databases in $AWSY/db/ will be created by month by default. Once
  the data is exported to .gz and no further builds for this month are of
  interest, either delete the database, or archive it with util/archive_db.sh
  (which drops indexes and compresses it to save space, usually >90%)


## How the mozilla test box is setup

The test box is an Ubuntu 64 LTS system. Aside from just cloning this repo, it
has the following setup.

- The tester and cron jobs run as user 'awsy'. The tester runs in a tmux session
  named areweslimyet
- `~/.ssh/authorized_keys` has a ssh key used by :kats' mobile-awsy test daemon
  (separate from this repo), with forced command set to
  tester_scripts/mobile_scp_only.sh so it can only write to /media/awsy/mobile/
- :kats pushes files consumable by util/import_flatfile.py to /media/awsy/mobile
  from the mobile-awsy setup (see mobile-awsy repo)
- `/media/awsy/nginx/` hosts the TP5 pageset on localhost:8001-8100
- `/media/awsy/nginx_local/` hosts nginx on port 8000 for the local AWSY website
- `/media/awsy/thttpd/` handles the localhost:8000/status/request.cgi script,
since nginx cannot do native cgi
- `/media/awsy/tester_scripts/start_httpd.sh` is run @reboot to start the three
  above webservices.
- `~/.vnc/` is setup with a default empty vnc config so the tester can run
e.g. 'vncserver :9' successfully, required for tests to run
- `/media/awsy/py2env/` is sourced by all the tester scripts, and just has mozmill
1.5 and mercurial in it
- `/media/awsy/mozilla-inbound/` is created, per above.
- `/media/awsy/db` created, per above.
- `/media/awsy/tester_scripts/cron.sh` run on a five-minute cron job.
- `/media/awsy/tester_scripts/start_tester_tmux.sh` is run @reboot, to launch
the tester in an attachable tmux session.

## These files

- `./cron.sh` is run on a five minute cron job, and runs the create_graph_json.py
  and merge_graph_json.py scripts, as well as ./import.sh. It also compresses
  old log files from the tester. It then pushes, via rsync, to
  nemu.pointysoftware.net, which is run by :johns, and hosts the public
  areweslimyet.com mirror.
  - `*/5 * * * * flock -n /media/awsy/cron.lck /media/awsy/tester_scripts/cron.sh`
- `./import.sh` runs util/import_flatfile.py on all files in /media/awsy/mobile.
- `./start_tester_tmux.sh` is run in a cron @reboot job to make a tmux session and
  stuff ./launch_tester.sh into it.
- `./launch_tester.sh` launches the benchtester/BatchTester.py daemon to run
  automated tests reading from html/status/
- `./mobile_scp_only.sh` is used as an .ssh/authorized_keys hook to allow the
  awsy-mobile daemon to write to /media/awsy/mobile/ only
- `slimtest.mozconfig` is used for 'compile' type builds. Don't use
  these. Someone should delete all support for them.
- `start_httpd.sh` is run on @reboot to launch
  /media/awsy/{nginx,nginx_local,thttpd)
- `start_tester_tmux.sh` runs ./launch_tester.sh in a tmux session
- `tp5.nginx.conf` is the example nginx.conf used by /media/awsy/nginx/ to host
  tp5 on 100 ports due to reasons.
