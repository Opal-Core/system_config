#!/bin/bash
logger "REST API: Running diagnostic file generation"
SYSLOG_PATH="/var/log/syslog*"
BASE_LOCATION="/home/snuc/SDKVM"
DIAGNOSTICS_LOCATION="/home/snuc/SDKVM/diagnostics"
OPENBOX_LOG="/home/snuc/.cache/openbox/openbox.log"
MONITOR_MANAGEMENT="/home/snuc/.config/monitor-management"
PERFORMANCE_STATISTICS="/home/snuc/SDKVM/debug"
logger "OSD:  Diagnostic FIles: Removing any existing files in $DIAGNOSTICS_LOCATION."
rm -rf $DIAGNOSTICS_LOCATION/*
logger "OSD:  Diagnostic FIles: Creating diagnostics files in $DIAGNOSTICS_LOCATION."
logger "OSD: Diagnostic FIles: Copying diagnostic files to $DIAGNOSTICS_LOCATION"
(cd $DIAGNOSTICS_LOCATION; cp -d $SYSLOG_PATH .; rm -rf *.gz)
(cd $DIAGNOSTICS_LOCATION; cp -R $OPENBOX_LOG .)
(cd $DIAGNOSTICS_LOCATION; cp -L $MONITOR_MANAGEMENT/* .)
(cd $DIAGNOSTICS_LOCATION; cp -L $PERFORMANCE_STATISTICS/* .)
logger "OSD: Diagnostic FIles: Copied $SYSLOG_PATH $MONITOR_MANAGEMENT,$PERFORMANCE_STATISTICS and  $OPENBOX_LOG to $DIAGNOSTICS_LOCATION"



