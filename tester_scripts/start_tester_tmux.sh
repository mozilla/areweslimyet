#!/bin/bash

cd "$(dirname "$0")"

tmux new -d -s areweslimyet './launch_tester.sh; echo Tester exited, press any key; read'
