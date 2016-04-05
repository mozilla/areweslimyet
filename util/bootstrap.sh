#!/usr/bin/env bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# A simple server setup script. This assumes the server is an ubuntu machine.
# Files etc, will be installed under the pwd.

# Directory to install source code and other files to. $AWSY_USER will own
# this directory.
INSTALL_DIR="${PWD}/areweslimyet"

# Capture the full script path for use later.
SCRIPT_PATH=$(readlink -f $0)

# User to run AWSY under. Set this to $USER if you want to run as yourself.
AWSY_USER="awsy"

# Install required system pacakges.
# NB: This assumes a debian/ubuntu system. On Fedora/Cent we could switch out:
#     python-dev=>python-devel, sqlite3=>sqlite, tightvncserver=>tigervnc-server
#     and use |yum install|.
PACKAGES="git nginx python-dev python-virtualenv python-pip sqlite3 tightvncserver curl"
sudo apt-get -q install $PACKAGES

if [ $? -ne 0 ]; then
  echo "Failed to install required packages"
  exit 1
fi

# Check to make sure access to required network resources are available. This
# helps diagnose issues with systems behind a firewall or proxy.
URLS="https://archive.mozilla.org https://github.com https://hg.mozilla.org http://pypi.python.org"
for URL in $URLS; do
  if ! curl -sfL -o /dev/null $URL; then
    echo "unable to connect directly to $URL"
    exit 2
  fi
done

TCP_CONNS="pulse.mozilla.org:5671"
for TCP_CONN in $TCP_CONNS; do
  IFS=':' read SERVER PORT <<< "$TCP_CONN"
  if ! nc -w 5 -vz $SERVER $PORT; then
    echo "unable to connect to $TCP_CONN"
    exit 2
  fi
done

# Create an awsy user
if ! getent passwd $AWSY_USER 2&> /dev/null; then
  echo "Adding '$AWSY_USER' user..."
  # NB: Specifying the user is a "system" user and lives under /var helps
  #     prevent puppet from nuking our account on datacenter machines.
  sudo useradd --system --create-home --b /var $AWSY_USER
else
  echo "$AWSY_USER user already exists"
fi

# Create install dir, hand it over to the awsy user
if [ ! -d "$INSTALL_DIR" ]; then
  mkdir "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"
sudo chown ${AWSY_USER}:${AWSY_USER} .

# Perform the rest as the awsy user
tail -n +$[LINENO+2] "$SCRIPT_PATH" | exec sudo -H -u $AWSY_USER bash
exit $?
function setup_as_awsy() {
  # Password used for VNC sessions, these sessions are internal only so this
  # is just a required formality. Comment this out if you're paranoid and want
  # to set your own.
  VNC_PASSWD="slimyet"
  VENV="marionette-env"

  # Checkout the repo
  git clone https://github.com/mozilla/areweslimyet.git .

  # Create virtualenv, enter it.
  virtualenv $VENV
  source "$VENV/bin/activate"

  # Install pip packages
  if ! pip install -r "requirements.txt"; then
    echo "Failed to install python requirements"
    exit 3
  fi

  # Exit the virtual env.
  deactivate

  # Required to run slimtest.
  mkdir -p db

  # Required for batchtester cron job.
  touch last_tinderbox.json
  mkdir -p html/status/batch

  # Setup a vnc password.
  VNC_DIR="${HOME}/.vnc"
  if [ ! -d "$VNC_DIR" ]; then
    echo "Setting VNC password"
    if [ -n "$VNC_PASSWD" ]; then
      mkdir "$VNC_DIR"
      chmod 700 "$VNC_DIR"
      echo -n "$VNC_PASSWD" | vncpasswd -f > "$VNC_DIR/passwd"
      chmod 600 "$VNC_DIR/passwd"
    else
      vncpasswd
    fi
  fi
}

setup_as_awsy
exit 0
