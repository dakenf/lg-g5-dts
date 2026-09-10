#!/bin/sh
# Run on the exact rooted TV from a freshly extracted release package.
set -eu
[ "${1:-}" = --install ] || { echo 'Usage: sh install.sh --install (on the rooted target TV)'; exit 0; }
cd "$(dirname "$0")"
[ "$(id -u)" = 0 ]
[ "$(uname -r)" = '5.4.268-329.ptl4tv.5' ]
[ -f /var/lib/webosbrew/startup.sh ]
sha256sum -c SHA256SUMS
for command in /usr/bin/python3 /usr/bin/script /usr/bin/timeout /usr/bin/luna-send /bin/systemctl; do
 [ -x "$command" ] || { echo "Missing prerequisite: $command" >&2; exit 1; }
done
base=/var/lib/lg-dts-core
stage=/var/lib/lg-dts-stage-$$
backup=/var/lib/lg-dts-backup-$(date +%s)-$$
mkdir -m 700 "$stage"
cp -a . "$stage/"
(cd "$stage" && sha256sum -c SHA256SUMS)
if systemctl cat lg-dts-core.service >/dev/null 2>&1; then systemctl stop lg-dts-core.service; fi
[ -z "$(lsmod | awk '$1=="dts_gate" || $1=="dts_core_route" {print $1}')" ] || {
 echo 'An experiment module is still loaded; restore it before installing.' >&2; exit 1;
}
[ ! -d "$base" ] || mv "$base" "$backup"
mv "$stage" "$base"
mkdir -p /var/lib/webosbrew/init.d
cp "$base/90-lg-dts-core" /var/lib/webosbrew/init.d/90-lg-dts-core
chmod 700 /var/lib/webosbrew/init.d/90-lg-dts-core
touch "$base/enabled"
sh /var/lib/webosbrew/init.d/90-lg-dts-core
systemctl is-active lg-dts-core.service
echo "Installed. Previous installation (if any): $backup"
echo 'Disable: sh /var/lib/lg-dts-core/control.sh disable'
