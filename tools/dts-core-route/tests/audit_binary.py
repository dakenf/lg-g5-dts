#!/usr/bin/env python3
"""Verify module ABI markers and resolve its imports in captured PREL32 exports."""
from pathlib import Path
import subprocess, struct, re, json
R=Path(__file__).resolve().parents[3]
b=(R/'inputs/kernel.bin').read_bytes()
module=Path(__import__('os').environ.get('DTS_AUDIT_MODULE',str(R/'build/package/dts_core_route.ko')))
stock=R/'inputs/stock-module.ko'
def run(*cmd):return subprocess.check_output(cmd,text=True)
def abi(path):
 sections=run('readelf','-SW',str(path))
 line=next(s for s in sections.splitlines() if '.gnu.linkonce.this_module ' in s and 'RELA' not in s)
 size=int(line.split('PROGBITS')[1].split()[2],16)
 mod=run('readelf','-p','.modinfo',str(path))
 magic=next(l.split('vermagic=')[1] for l in mod.splitlines() if 'vermagic=' in l)
 rel=run('readelf','-rW',str(path)).split("Relocation section '.rela.gnu.linkonce.this_module'")[1]
 offsets={name:int(re.search(r'^([0-9a-f]+).* '+name+r' \+',rel,re.M).group(1),16) for name in ('init_module','cleanup_module')}
 return {'size':size,'vermagic':magic,**offsets}
assert abi(module)==abi(stock)
names=[l.split()[-1] for l in run('llvm-nm','-u',str(module)).splitlines()]
positions={}
for name in names:
 needle=b'\0'+name.encode()+b'\0';p=0
 while (p:=b.find(needle,p))>=0:
  positions[p+1]=name;p+=1
found={}
for p,(rel,) in enumerate(struct.iter_unpack('<i',b[:len(b)//4*4])):
 at=p*4;name=positions.get(at+rel)
 if name and at>=4 and at+8<=len(b):
  val=at-4+struct.unpack_from('<i',b,at-4)[0]
  ns=at+4+struct.unpack_from('<i',b,at+4)[0]
  if 0<=val<0x2700000 and 0<=ns<len(b) and b[ns]==0:
   found[name]={'entry_file_offset':hex(at-4),'runtime':hex(0xffffffc010088000+val)}
missing=set(names)-set(found)
assert not missing, f'Unresolved captured-kernel exports: {missing}'
report={'abi':abi(module),'exports':found,'status':'PASS'}
(R/'build/reports/binary-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: stock module ABI markers match; all module imports found in captured kernel exports')
