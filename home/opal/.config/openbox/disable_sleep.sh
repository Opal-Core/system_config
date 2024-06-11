#!/bin/bash
source /home/opal/.config/openbox/defines.sh

write_to_log "Disabling system sleep"
xset -dpms     # Disable DPMS (Energy Star) features
xset s off     # Disable screensaver
xset s noblank # Don't blank video device
