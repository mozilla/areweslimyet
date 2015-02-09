#!/bin/bash

cd "$(dirname "$0")"

tmux new -d -s trywatcher './launch_trywatcher.sh; echo Try Watcher exited, press any key; read'
