#!/usr/bin/env python3
"""Verify/regenerate guards for the known raw image. Never an automatic porter."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--kernel', type=Path, default=ROOT / 'inputs/kernel.bin')
p.add_argument('--check', action='store_true', help='verify without writing')
a = p.parse_args()
manifest = json.loads((ROOT / 'tools/dts-core-route/target.json').read_text())
raw = a.kernel.read_bytes()
if hashlib.sha256(raw).hexdigest() != manifest['kernel_sha256']:
    raise SystemExit('Refusing unknown kernel image; see docs/porting.md.')
base = int(manifest['runtime_base'], 16)
lines = ['/* Generated from the captured, unmodified 33.30.80 kernel. */\n']
for name, address in manifest['addresses'].items():
    lines.append(f'#define {name} {address}UL\n')
lines.append('static const struct { unsigned long addr; unsigned char bytes[64]; } target_checks[] = {\n')
for name, check in manifest['checks'].items():
    offset = int(check['file_offset'], 16)
    expected = bytes.fromhex(check['hex'])
    assert len(expected) == 64 and raw[offset:offset + 64] == expected, name
    assert base + offset == int(check['runtime'], 16), name
    values = ','.join(f'0x{x:02x}' for x in expected)
    lines.append(f"    {{{check['runtime']}UL, {{{values}}}}}, /* {name} */\n")
lines.append('};\n')
common = ''.join(lines)
hd = ['static const struct { unsigned long addr; unsigned char bytes[64]; } status_checks[] = {\n']
for offset in (0xeb356c, 0xeb362c, 0xeb2e64):
    values = ','.join(hex(x) for x in raw[offset:offset + 64])
    hd.append(f' {{{hex(base + offset)}UL, {{{values}}}}},\n')
hd.append('};\n')
outputs = {
    ROOT / 'tools/dts-core-route/target.h': common,
    ROOT / 'tools/dts-hd-route/target.h': common,
    ROOT / 'tools/dts-hd-route/status_guards.h': ''.join(hd),
}
for path, content in outputs.items():
    if a.check:
        assert path.read_text() == content, f'Guard mismatch: {path}'
    else:
        path.write_text(content)
# Gate has a separate instruction-sized guard, not a 64-byte target entry.
assert raw[0xef1130:0xef1138] == bytes.fromhex('00008052c0035fd6')
print('PASS: known image, common fingerprints, HD guards and gate verified' if a.check else 'Generated known-target guards')
