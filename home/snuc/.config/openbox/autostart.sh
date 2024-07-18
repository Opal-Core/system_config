#!/bin/bash

# initiallise_log
logger "Openbox: Adding background images using feh" 
feh --bg-scale /home/snuc/.config/openbox/background.png &

logger "Openbox: Disable sleep" 
/home/snuc/.config/openbox/disable_sleep.sh
