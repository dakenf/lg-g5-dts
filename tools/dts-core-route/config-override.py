#!/usr/bin/env python3
"""Reapply the volatile EDID override at service start; restore owned changes."""
import json
import os
import subprocess
import sys
import time

KEY = 'tv.model.edidType'
TARGET = 'TrueHD+dts'
STOCK = 'TrueHD'
STATE = '/var/lib/lg-dts-core/config-original.json'


def luna(method, payload):
    # Payloads contain only our fixed keys and the two validated enum strings.
    # util-linux script supplies the terminal required by this TV's luna-send.
    command = "/usr/bin/luna-send -w 4000 -n 1 luna://com.webos.service.config/" + method
    command += " '" + json.dumps(payload) + "'"
    raw = subprocess.check_output(
        ['/usr/bin/timeout', '6', '/usr/bin/script', '-q', '-e', '-c', command, '/dev/null'],
        stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, timeout=8)
    result = json.loads(raw.decode().strip())
    if result.get('returnValue') is not True:
        raise RuntimeError('configd rejected ' + method)
    return result


def get_value():
    return luna('getConfigs', {'configNames': [KEY]})['configs'][KEY]


def set_value(value):
    if value not in (STOCK, TARGET):
        raise RuntimeError('Unexpected EDID value')
    luna('setConfigs', {'configs': {KEY: value}})
    if get_value() != value:
        raise RuntimeError('EDID readback mismatch')


def refresh_arc():
    subprocess.run(['/usr/bin/timeout', '20', '/bin/systemctl', 'restart', 'arccontroller.service'],
                   check=True, timeout=22)


def save_original():
    temporary = STATE + '.tmp-' + str(os.getpid())
    with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as f:
        json.dump({'original': STOCK}, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporary, STATE)


def ensure():
    deadline = time.monotonic() + 90
    while True:
        try:
            value = get_value()
            break
        except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError):
            if time.monotonic() >= deadline:
                raise RuntimeError('configd did not become ready within the startup window')
            time.sleep(2)
    if value not in (STOCK, TARGET):
        raise RuntimeError('Refusing unexpected EDID configuration: ' + str(value))
    if value == STOCK:
        # Journal before mutation, including a setter whose response is lost.
        save_original()
        set_value(TARGET)
    # Also refresh already-enabled setups: the ARC service may cache older caps.
    refresh_arc()
    print('DTS EDID verified; ARC capabilities refreshed', flush=True)


def restore():
    if not os.path.exists(STATE):
        print('No owned EDID change to restore', flush=True)
        return
    with open(STATE) as f:
        if json.load(f) != {'original': STOCK}:
            raise RuntimeError('Invalid saved EDID state; refusing restoration')
    current = get_value()
    if current == TARGET:
        set_value(STOCK)
        refresh_arc()
    elif current == STOCK:
        # A previous restoration may have failed after changing configd.
        refresh_arc()
    else:
        print('EDID changed externally; preserving its current value', flush=True)
    os.unlink(STATE)
    print('Owned EDID override released', flush=True)


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ('ensure', 'restore', 'status'):
        sys.exit('Usage: config-override.py ensure|restore|status')
    if os.geteuid() != 0 or os.uname().release != '5.4.268-329.ptl4tv.5':
        sys.exit('Requires the exact rooted target kernel')
    try:
        if sys.argv[1] == 'status':
            print(get_value())
        else:
            globals()[sys.argv[1]]()
    except Exception as error:
        sys.exit('DTS configuration error: ' + str(error))
