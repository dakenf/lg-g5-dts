#!/bin/sh
# Session supervisor. Unsupported formats remain with the normal LG stack.
set -eu
cd "$(dirname "$0")"
# Keep one bounded-size diagnostic log in volatile storage.
if [ -f /tmp/lg-dts.log ] && [ "$(wc -c < /tmp/lg-dts.log)" -gt 1048576 ]; then mv /tmp/lg-dts.log /tmp/lg-dts.log.old; fi
exec >> /tmp/lg-dts.log 2>&1
child=''
stop() {
    trap - TERM INT HUP
    if [ -n "$child" ]; then
        kill -TERM "$child" 2>/dev/null || true
        wait "$child" || true
    fi
    exit 0
}
trap stop TERM INT HUP
while :; do
    runner=''
    if grep -qx 'AudioData=1' /proc/lgtv-driver/audio/hdmi &&
       grep -qx 'Connect=HDMI_PORT2' /proc/lgtv-driver/audio/adec.p1 &&
       grep -q 'EArcOnOff=On' /proc/lgtv-driver/audio/sndout; then
        if grep -qx 'Codec=DTS' /proc/lgtv-driver/audio/hdmi &&
           grep -qx 'SamplingRate=48000' /proc/lgtv-driver/audio/hdmi; then
            runner=./run-on-tv.sh
        elif grep -qx 'Codec=DTS_HD' /proc/lgtv-driver/audio/hdmi &&
             grep -qx 'SamplingRate=192000' /proc/lgtv-driver/audio/hdmi; then
            runner=./hd/run-on-tv.sh
        fi
    fi
    if [ -n "$runner" ]; then
        echo "Starting $runner"
        sh "$runner" --session &
        child=$!
        result=0
        wait "$child" || result=$?
        child=''
        case "$result" in 0|10) ;; *) echo "DTS session failed ($result); not retrying automatically"; exit "$result";; esac
    fi
    sleep 2 &
    child=$!
    wait "$child" || true
    child=''
done
