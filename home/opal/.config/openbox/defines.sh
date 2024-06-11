#!/bin/bash
export OPENBOX_STARTUP_LOG=/home/opal/.config/openbox/openbox_startup.log
export OPENBOX_PATH="/home/opal/.config/openbox"


timestamp() {
  date +"%T" # current time
}


initiallise_log() {
    echo ""  >  $OPENBOX_STARTUP_LOG
}

write_to_log() {
    DATE=`date +'%T'`
    echo  "$DATE : $1 " >>  $OPENBOX_STARTUP_LOG
}
