#!/bin/sh
set -eu
base=/var/lib/lg-dts-core
case "${1:-status}" in
 status) systemctl status lg-dts-core.service --no-pager;;
 start) systemctl start lg-dts-core.service;;
 stop) systemctl stop lg-dts-core.service;;
 enable) touch "$base/enabled"; sh /var/lib/webosbrew/init.d/90-lg-dts-core;;
 disable) rm -f "$base/enabled"; systemctl stop lg-dts-core.service;;
 *) echo 'Usage: control.sh status|start|stop|enable|disable'; exit 2;;
esac
