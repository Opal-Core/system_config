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
  LANIFACE=`/usr/bin/libsystem_cli --eth-interface`
  
  logger "Factory Restore: Removing existing network configurations"
  nmcli --terse connection show | cut -d : -f 1 | \
    while read name; do nmcli connection delete "$name"; done

  logger "Factory Restore: Setting default IP address for interface: [$LANIFACE]"
  nmcli con add type ethernet con-name 'static-ip' ifname $LANIFACE ipv4.method manual ipv4.addresses 192.168.1.10/24 gw4 192.168.1.1

  logger "Factory Restore: Setting default static-ip for $LANIFACE as active connection"
  nmcli con up id 'static-ip'
}

parse_args "$@"

# Terminating existing connections and workspaces on restore
# Copy default config file and dont overwrite if exists

# Stop all the opal proxy servers
if [[ -f "/usr/sbin/update-service" ]]; then
    echo "Stopping running opal proxy servers"
    if [[ -e "/etc/service/vm0" ]]; then
        sudo update-service -r /var/lib/supervise/vm0
    fi

    if [[ -e "/etc/service/vm1" ]]; then
        sudo update-service -r /var/lib/supervise/vm1
    fi

    if [[ -e "/etc/service/vm2" ]]; then
        sudo update-service -r /var/lib/supervise/vm2
    fi

    if [[ -e "/etc/service/vm3" ]]; then
        sudo update-service -r /var/lib/supervise/vm3
    fi

    if [[ -e "/etc/service/vm4" ]]; then
        sudo update-service -r /var/lib/supervise/vm4
    fi

    if [[ -e "/etc/service/vm5" ]]; then
        sudo update-service -r /var/lib/supervise/vm5
    fi

    if [[ -e "/etc/service/vm6" ]]; then
        sudo update-service -r /var/lib/supervise/vm6
    fi

    if [[ -e "/etc/service/vm7" ]]; then
        sudo update-service -r /var/lib/supervise/vm7
    fi
fi

# Delete all the config files and proxy server links from /home/opal/proxy/config
find /home/opal/proxy/config/ -maxdepth 1 -type f,l -delete

# Copy default files back to /home/opal/proxy/config
cp -n /home/opal/proxy/config/default/config-vm?.ini /home/opal/proxy/config

# Link proxy server to default configs
ln -sf /home/opal/proxy/config/config-vm0.ini /home/opal/proxy/config/vm0
ln -sf /home/opal/proxy/config/config-vm1.ini /home/opal/proxy/config/vm1
ln -sf /home/opal/proxy/config/config-vm2.ini /home/opal/proxy/config/vm2
ln -sf /home/opal/proxy/config/config-vm3.ini /home/opal/proxy/config/vm3
ln -sf /home/opal/proxy/config/config-vm4.ini /home/opal/proxy/config/vm4
ln -sf /home/opal/proxy/config/config-vm5.ini /home/opal/proxy/config/vm5
ln -sf /home/opal/proxy/config/config-vm6.ini /home/opal/proxy/config/vm6
ln -sf /home/opal/proxy/config/config-vm7.ini /home/opal/proxy/config/vm7

# Reset PASSWORD file to empty
echo 'admin' > /home/opal/PASSWORD

# Ensure opal system user has access to its own files
logger "Factory Restore: Setting opal file ownership to opal"
chown -R opal /home/opal/

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
