#!/bin/bash
# set -x
logger "Factory Restore: Restoring to defaults"
IGNORE_NETWORK=false

parse_args() {
    for arg in "$@"; do
        if [[ "$arg" == "--ignore-network" ]]; then
            IGNORE_NETWORK=true
        fi
    done
}

# Delete all connections and re-create network connection with default static-ip
reset_network() {
  LANIFACE=`/usr/local/bin/libsystem_cli --eth-interface`
  
  logger "Factory Restore: Removing existing network configurations"
  nmcli --terse connection show | cut -d : -f 1 | \
    while read name; do nmcli connection delete "$name"; done

  logger "Factory Restore: Setting default IP address for interface: [$LANIFACE]"
  nmcli con add type ethernet con-name 'static-ip' ifname $LANIFACE ipv4.method manual ipv4.addresses 192.168.1.21/24 gw4 192.168.1.1

  logger "Factory Restore: Setting default static-ip for $LANIFACE as active connection"
  nmcli con up id 'static-ip'
}

parse_args "$@"

# Terminating existing connections and workspaces on restore
# Removing users directory and all contents
# Removing OSD settings
# Remove Boxilla files
# Clean temp locations
# clean backup locations
# clean upgrade location
# Stop services

# Restore network configurations
if [[ $IGNORE_NETWORK == false ]]; then
    reset_network
else
    logger "Factory Restore: Option to not reset the network has been set."
fi

# Restart services
# Restart OSD

logger "Factory Restore: The restore process has completed."
