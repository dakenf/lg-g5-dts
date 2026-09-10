#!/usr/bin/env python3
"""Create a checksummed, explicit-file install package; never contact a TV."""
import argparse,hashlib,json,shutil,tarfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--prebuilt',action='store_true');a=p.parse_args()
b=R/'build/package'
if b.exists():shutil.rmtree(b)
(b/'hd').mkdir(parents=True)
if a.prebuilt:
 src=R/'prebuilt/33.30.80'
 for line in (src/'SHA256SUMS').read_text().splitlines():
  expected,name=line.split()
  if hashlib.sha256((src/name).read_bytes()).hexdigest()!=expected:
   raise SystemExit(f'Prebuilt checksum mismatch: {name}')
 mods=[(src/'core-route.ko','dts_core_route.ko'),(src/'dts-gate.ko','dts_gate.ko'),(src/'hd-route.ko','hd/dts_core_route.ko')]
else:
 mods=[(R/'tools/dts-core-route/dts_core_route.ko','dts_core_route.ko'),(R/'tools/dts-kernel-probe/dts_gate.ko','dts_gate.ko'),(R/'tools/dts-hd-route/dts_core_route.ko','hd/dts_core_route.ko')]
for src,n in mods:shutil.copyfile(src,b/n)
shutil.copyfile(b/'dts_gate.ko',b/'hd/dts_gate.ko')
for n in ['config-override.py','run-on-tv.sh','watch.sh','control.sh','lg-dts-core.service','90-lg-dts-core']:shutil.copyfile(R/'tools/dts-core-route'/n,b/n)
shutil.copyfile(R/'tools/dts-hd-route/run-on-tv.sh',b/'hd/run-on-tv.sh')
shutil.copyfile(R/'scripts/install-on-tv.sh',b/'install.sh')
(b/'manifest.json').write_text(json.dumps({'target':'OLED77G5RLA 33.30.80','kernel':'5.4.268-329.ptl4tv.5','input':'HDMI3','output':'eARC','origin':'tested binaries' if a.prebuilt else 'local build'},indent=2)+'\n')
def sums(folder,names):
 (folder/'SHA256SUMS').write_text(''.join(hashlib.sha256((folder/n).read_bytes()).hexdigest()+'  '+n+'\n' for n in names))
sums(b/'hd',['dts_core_route.ko','dts_gate.ko','run-on-tv.sh'])
names=sorted(str(x.relative_to(b)) for x in b.rglob('*') if x.is_file())
sums(b,names)
archive=R/'build/lg-g5-dts-33.30.80.tar.gz'
with tarfile.open(archive,'w:gz') as t:
 for n in names+['SHA256SUMS']:t.add(b/n,arcname=n)
print(archive)
