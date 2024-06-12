#!/bin/bash

logger "Alt Log Rotate starting with force"
/usr/sbin/logrotate -f /etc/logrotate.conf
logger "Alt Log Rotate Complete"
