#!/bin/bash

# initiallise_log
logger "Disabling Virtual Terminal Switching"
setxkbmap -option srvrkeys:none

logger "Setting session ID"
echo "0" > /tmp/session_id

# Start Discovery
#logger "Openbox autostart: Starting Discovery service"
#/usr/bin/startdiscovery.sh

# Start Webservice
#logger "Openbox autostart: Starting Webservice service"
#/usr/bin/startwebservice.sh
#sleep 2

# Start internal rest handler
#logger "Openbox autostart: Starting internal rest handler service"
#/usr/bin/startresthandler.sh

# Start Hotkeys handler
#logger "Openbox autostart: Starting BB Hotkeys service"
#/usr/bin/starthotkeys.sh

logger "OSD Post Connect: Adding background images using feh" 
feh --bg-scale /home/opal/.config/openbox/background.png &
/home/opal/.config/openbox/disable_sleep.sh

# We must again disable ctrl alt + function key 
logger "Disabling [Ctrl + Alt + Function key] combinations using xmodmap"
xmodmap /etc/custom.Xmodmap 2>&1 | logger
