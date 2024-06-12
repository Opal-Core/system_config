#!/bin/bash

SYSTEM_MANAGER_PATH=/home/opal/gateway/system_manager.py
application="System Manager"

if wmctrl -xl | grep "${application}" > /dev/null ; then
    # Already running, raising to front
    wmctrl -x -R "$application"
else
    # Not running: starting with application path
    logger "Starting System Manager"
    /usr/bin/python3 $SYSTEM_MANAGER_PATH #specify application path
fi
