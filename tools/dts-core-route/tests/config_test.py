#!/usr/bin/env python3
"""Boot config lifecycle with fake configd/ARC; no device access."""
import importlib.util
import json
import pathlib
import tempfile
from unittest.mock import patch

path = pathlib.Path(__file__).resolve().parents[1] / 'config-override.py'
spec = importlib.util.spec_from_file_location('config_override', path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

cases = ('boot', 'already_enabled', 'late_configd', 'never_ready', 'unknown',
         'setter_lost_reply', 'bad_readback', 'arc_failure', 'external_change',
         'invalid_journal', 'repeat_restore', 'reboot')
for case in cases:
    with tempfile.TemporaryDirectory() as folder:
        m.STATE = folder + '/original.json'
        state = {'value': m.TARGET if case == 'already_enabled' else m.STOCK, 'reads': 0, 'writes': [], 'arc': 0}
        if case == 'unknown': state['value'] = 'pcm'
        def get():
            state['reads'] += 1
            if case == 'never_ready' or (case == 'late_configd' and state['reads'] < 3):
                raise RuntimeError('configd starting')
            return state['value']
        def call(method, payload):
            if method == 'getConfigs':
                return {'returnValue': True, 'configs': {m.KEY: get()}}
            value = payload['configs'][m.KEY]
            # A write must never precede the ownership journal.
            assert pathlib.Path(m.STATE).exists()
            state['writes'].append(value)
            if case != 'bad_readback' or value != m.TARGET: state['value'] = value
            if case == 'setter_lost_reply' and value == m.TARGET: raise RuntimeError('reply lost')
            return {'returnValue': True}
        def arc():
            state['arc'] += 1
            if case == 'arc_failure' and state['arc'] == 1: raise RuntimeError('ARC unavailable')
        with patch.object(m, 'luna', call), patch.object(m, 'refresh_arc', arc), \
             patch.object(m.time, 'sleep'), patch.object(m.time, 'monotonic', side_effect=[0, 100] if case == 'never_ready' else [0]*100):
            failed = False
            try: m.ensure()
            except RuntimeError: failed = True
            assert failed == (case in ('never_ready', 'unknown', 'setter_lost_reply', 'bad_readback', 'arc_failure')), case
            if case in ('never_ready', 'unknown'):
                assert not state['writes'] and not pathlib.Path(m.STATE).exists()
                continue
            if case == 'already_enabled':
                m.restore()
                assert state['value'] == m.TARGET and not state['writes']
                continue
            if case == 'external_change': state['value'] = 'ac3'
            if case == 'invalid_journal':
                pathlib.Path(m.STATE).write_text(json.dumps({'original': 'pcm'}))
                try: m.restore()
                except RuntimeError: pass
                else: raise AssertionError('Invalid journal accepted')
                assert state['value'] == m.TARGET
                continue
            if case == 'reboot':
                state['value'] = m.STOCK
                m.ensure()
                assert state['value'] == m.TARGET
            m.restore()
            assert state['value'] == ('ac3' if case == 'external_change' else m.STOCK), case
            assert not pathlib.Path(m.STATE).exists(), case
            if case == 'repeat_restore':
                count = len(state['writes'])
                m.restore()
                assert len(state['writes']) == count
print(f'PASS: {len(cases)} boot configuration/rollback scenarios (mock configd and ARC)')
