#!/bin/sh
# Timed test or supervised session; payloads installed only by deployment.
set -eu
if [ "${1:-}" != '--apply' ] && [ "${1:-}" != '--session' ]; then
    echo 'DTS core controller. Nothing changed.'
    echo 'Later, on the exact TV: sh run-on-tv.sh --apply [15..60 seconds]'
    exit 0
fi
cd "$(dirname "$0")"
session=0
[ "$1" != --session ] || session=1
seconds=${2:-30}
case "$seconds" in ''|*[!0-9]*) exit 2;; esac
[ "$seconds" -ge 15 ] && [ "$seconds" -le 60 ] || exit 2
[ "$(id -u)" = 0 ]
[ "$(uname -r)" = '5.4.268-329.ptl4tv.5' ]
sha256sum -c SHA256SUMS
[ -z "$(lsmod | awk '$1=="dts_gate" || $1=="dts_core_route" {print $1}')" ]
core_now() {
    grep -qx 'AudioData=1' /proc/lgtv-driver/audio/hdmi &&
    grep -qx 'Codec=DTS' /proc/lgtv-driver/audio/hdmi &&
    grep -qx 'SamplingRate=48000' /proc/lgtv-driver/audio/hdmi &&
    grep -qx 'Connect=HDMI_PORT2' /proc/lgtv-driver/audio/adec.p1
}
core_now || { echo 'Requires live DTS core/48kHz on HDMI3; aborting.'; exit 1; }
grep -q 'EArcOnOff=On' /proc/lgtv-driver/audio/sndout
find_prop() {
    set -- /proc/aaudio/processors/dsp0/hdmi1/*/prop
    [ "$#" = 1 ] && [ -f "$1" ] || return 1
    printf '%s\n' "$1"
}
prop=$(find_prop)
grep -qx 'hdmi-port=(int)2' "$prop"
logdir="/tmp/dts-core-test-$(date +%s)-$$"
mkdir -m 700 "$logdir"
cp "$prop" "$logdir/original.prop"
cp /proc/lgtv-driver/audio/sndout "$logdir/original.sndout"
earc=$(amixer -c0 cget numid=92 | sed -n 's/^  : values=//p')
# Only use the known ordinary pass-through setting; do not force a new codec.
[ "$earc" = '2,1,0,0,1' ] || { echo 'Unexpected eARC control; aborting.'; exit 1; }
printf '%s\n' "$earc" > "$logdir/original.earc"
gate_loaded=0
route_loaded=0
modified=0
gain_prop=''
gain_modified=0
cleanup() {
    status=$?
    trap - EXIT HUP INT TERM
    set +e
    failed=0
    restore_input=0
    prop=$(find_prop) || prop=''
    # Source may disappear while our DSP instance still has its DTS override.
    # Quiesce that owned instance before removing the output-status hooks.
    if [ "$modified" = 1 ] && [ -f "$prop" ] &&
       grep -qx 'hdmi-port=(int)2' "$prop" &&
       { core_now || grep -qx 'codec=(int)5' "$prop"; }; then
        restore_input=1
        printf 'drop 1\n' > "$prop" || failed=1
        printf 'start 0\n' > "$prop" || failed=1
    fi
    if [ "$gain_modified" = 1 ] && [ "$restore_input" = 1 ] && [ -f "$gain_prop" ]; then
        for name in mute-input mute-output; do
            value=$(sed -n "s/^$name=([^)]*)//p" "$logdir/original.gain")
            printf '%s %s\n' "$name" "$value" > "$gain_prop" || failed=1
        done
    fi
    if [ "$restore_input" = 1 ]; then
        for name in codec mode data-drop-mode drop-output-data start drop; do
            value=$(sed -n "s/^$name=([^)]*)//p" "$logdir/original.prop")
            [ -n "$value" ] && printf '%s %s\n' "$name" "$value" > "$prop"
        done
        sleep 1
    fi
    if [ "$route_loaded" = 1 ]; then rmmod dts_core_route || failed=1; fi
    if [ "$gate_loaded" = 1 ]; then rmmod dts_gate || failed=1; fi
    if [ "$modified" = 1 ]; then
        # Let the driver calculate the new source's route from current controls.
        if ! core_now; then
            current_earc=$(amixer -c0 cget numid=92 | sed -n 's/^  : values=//p')
            [ -z "$current_earc" ] || earc=$current_earc
        fi
        amixer -c0 cset numid=92 "$earc" > "$logdir/restore-earc.txt" 2>&1 || failed=1
        systemctl restart extinput-integration.service || failed=1
    fi
    if [ -n "$(lsmod | awk '$1=="dts_gate" || $1=="dts_core_route" {print $1}')" ]; then failed=1; fi
    dmesg | grep -E 'dts_gate:|dts_core_route:' > "$logdir/module.log"
    cat /proc/lgtv-driver/audio/sndout > "$logdir/final.sndout"
    echo "Test ended; logs: $logdir; cleanup_errors=$failed"
    [ "$failed" = 0 ] || { echo 'Rollback incomplete; inspect modules and restart TV before other tests.'; exit 1; }
    exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP
insmod ./dts_gate.ko enable=1
gate_loaded=1
modified=1
systemctl restart extinput-integration.service
# Allow ordinary service startup to set ADEC1's codec and create bypass nodes.
i=0
while [ "$i" -lt 10 ]; do
    core_now || exit 1
    if grep -qx 'UserCodec=DTS' /proc/lgtv-driver/audio/adec.p1 &&
       grep -qx 'Start=1' /proc/lgtv-driver/audio/adec.p1; then break; fi
    i=$((i+1)); sleep 1
done
[ "$i" -lt 10 ] || { echo 'ADEC did not start; aborting.'; exit 1; }
prop=$(find_prop)
grep -qx 'hdmi-port=(int)2' "$prop"
# Load scope hook before provoking the normal eARC decision. Fingerprint
# verification is in the module; no force loading is used.
window=$((seconds+10))
[ "$session" = 0 ] || window=0
insmod ./dts_core_route.ko selftest_only=0 enable=1 window_seconds=$window
route_loaded=1
# Create the downstream connection while the input is stopped.
amixer -c0 cset numid=92 "$earc" > "$logdir/trigger-earc.txt"
cat /proc/aaudio/dot_block_connection > "$logdir/route-before-input.dot"
grep -q 'renderer_1_out100 -> mixer_0_in100' "$logdir/route-before-input.dot" || {
    echo 'Compressed route not created; aborting before input start.'; exit 1;
}
grep -q 'mixer_0_out100 -> output_3_in0' "$logdir/route-before-input.dot" || exit 1
# This exact renderer bypass gain is confirmed by the current module graph.
# UNKNOWN decoder status otherwise leaves it muted despite a connected route.
gain_prop=/proc/aaudio/processors/dsp2/gain/041b0001/prop
grep -q 'gain_041b0001_.* -> bypass_04160001_' /proc/aaudio/dot_module_connection
[ -f "$gain_prop" ]
cp "$gain_prop" "$logdir/original.gain"
for name in mute-input mute-output; do
    value=$(sed -n "s/^$name=([^)]*)//p" "$logdir/original.gain")
    case "$value" in true|false) ;; *) echo 'Unexpected gain property'; exit 1;; esac
done
gain_modified=1
printf 'mute-input false\n' > "$gain_prop"
printf 'mute-output false\n' > "$gain_prop"
printf 'codec 5\n' > "$prop"
printf 'mode 1\n' > "$prop"
printf 'data-drop-mode 1\n' > "$prop"
printf 'drop-output-data false\n' > "$prop"
printf 'start 1\n' > "$prop"
printf 'drop 0\n' > "$prop"
if [ "$session" = 1 ]; then echo "DTS core supervised session active"; else
    echo "DTS core test running for $seconds seconds. Check Q950A audio/format display."
fi
i=0
while { [ "$session" = 1 ] || [ "$i" -lt "$seconds" ]; }; do
    sleep 1
    core_now || { echo 'Input changed; ending test.'; [ "$session" = 0 ] && exit 1; exit 10; }
    i=$((i+1))
    sample=$i
    [ "$session" = 0 ] || sample=latest
    cat "${prop%/prop}/lstatus" > "$logdir/hdmi-$sample.txt"
    cat /proc/lgtv-driver/audio/sndout > "$logdir/sndout-$sample.txt"
    cat "$gain_prop" > "$logdir/gain-$sample.txt"
done
cat /proc/aaudio/dot_block_connection > "$logdir/final.dot"
cat "$prop" > "$logdir/test.prop"
# Successful script execution is NOT proof of audible sound or DTS lock.
