#!/bin/bash
# we should pass the path and name of the diagnostics log we wish to create, for example
# ./diagnostics.sh /home/snuc/SDKVM/diagnostics/diagnostics.log
logger "REST API: Running diagnsotics"
FULL_PATH=$1
FILE_PATH=$(dirname "$FULL_PATH")
FILE_NAME=$(basename "$FULL_PATH")
SYSLOG_PATH="/var/log/syslog*"
BASE_LOCATION="/home/snuc/SDKVM"
TEMP_LOCATION="$BASE_LOCATION/temp"
DIAGNOSTICS_LOCATION="/home/snuc/SDKVM/diagnostics"
OSD_LOGS_LOCATION="/home/snuc/SDKVM/logs"
OSD_LOG="/home/snuc/SDKVM/logs/osd.log"
SYSTEM_SETTINGS=/home/snuc/SDKVM/system_level_settings.json
OPENBOX_LOG="/home/snuc/.cache/openbox/openbox.log"
MONITOR_MANAGEMENT="/home/snuc/.config/monitor-management"
PERFORMANCE_STATISTICS="/home/snuc/SDKVM/debug"
logger "OSD:  Diagnostics: Removing any existing files in $DIAGNOSTICS_LOCATION."
rm -rf $DIAGNOSTICS_LOCATION/*
logger "OSD:  Diagnostics: Removing any existing files in $TEMP_LOCATION."
rm -rf $TEMP_LOCATION
mkdir -p $TEMP_LOCATION
logger "OSD:  Diagnostics: Creating diagnostics files in $FULL_PATH."
logger "OSD: Diagnostics: Creating diagnostic file $DIAGNOSTICS_LOCATION/$FILE_NAME"
(cd $DIAGNOSTICS_LOCATION; cp -R $SYSLOG_PATH $TEMP_LOCATION/)
(cd $OSD_LOGS_LOCATION; cp -R $OSD_LOG $TEMP_LOCATION/)
(cd $BASE_LOCATION; cp -R $SYSTEM_SETTINGS $TEMP_LOCATION/)
(cd $DIAGNOSTICS_LOCATION; cp -R $OPENBOX_LOG $TEMP_LOCATION/)
(cd $DIAGNOSTICS_LOCATION; cp -R $MONITOR_MANAGEMENT $TEMP_LOCATION/ )
(cd $DIAGNOSTICS_LOCATION; cp -R $PERFORMANCE_STATISTICS $TEMP_LOCATION/ )
logger "OSD: Diagnostics: Copied $SYSLOG_PATH,$MONITOR_MANAGEMENT,$PERFORMANCE_STATISTICS and $OPENBOX_LOG to $TEMP_LOCATION"
(cd $TEMP_LOCATION; tar -zcf $FILE_NAME.tar.gz *)
logger "OSD: Diagnostics: Copying  $TEMP_LOCATION/$FILE_NAME $DIAGNOSTICS_LOCATION/$FILE_NAME"
(cd $TEMP_LOCATION; openssl enc -aes-256-cbc -md sha512 -pbkdf2 -iter 100000 -salt -in $FILE_NAME.tar.gz -out $FULL_PATH -pass pass:PASS234221156)
#rm -rf $TEMP_LOCATION


