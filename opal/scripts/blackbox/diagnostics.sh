#!/bin/bash
# we should pass the path and name of the diagnostics log we wish to create, for example
# ./diagnostics.sh /home/snuc/SDKVM/diagnostics/diagnostics.log
logger "REST API: Running diagnsotics"

FULL_PATH=$1
FILE_PATH=$(dirname "$FULL_PATH")
FILE_NAME=$(basename "$FULL_PATH")
SYSLOG_PATH="/var/log/syslog*"
BASE_LOCATION="/home/opal/SDKVM"
DIAGNOSTICS_LOCATION="/home/opal/SDKVM/diagnostics"
TMP_LOCATION="$DIAGNOSTICS_LOCATION/tmp"

logger "Diagnostics: Removing any existing files in $DIAGNOSTICS_LOCATION"
rm -rf $DIAGNOSTICS_LOCATION/*
mkdir -p $DIAGNOSTICS_LOCATION

logger "Diagnostics: Removing any existing files in $TMP_LOCATION"
rm -rf $TMP_LOCATION
mkdir -p $TMP_LOCATION

logger "Diagnostics: Creating diagnostics files in $FULL_PATH"
logger "Diagnostics: Creating diagnostic file $DIAGNOSTICS_LOCATION/$FILE_NAME"
(cd $DIAGNOSTICS_LOCATION; cp -R $SYSLOG_PATH $TMP_LOCATION/)

logger "Diagnostics: Copied $SYSLOG_PATH to $TMP_LOCATION"

logger "Diagnostics: Zipping with encryption"
cd $TMP_LOCATION
zip -P "PASS234221156" -R "$FULL_PATH" "*"
logger "Diagnostics: Created archive at $FULL_PATH"

logger "Diagnostics: Cleaning up $TMP_LOCATION"
(cd $DIAGNOSTICS_LOCATION; rm -rf $TMP_LOCATION)

logger "REST API: Diagnostics collected"
