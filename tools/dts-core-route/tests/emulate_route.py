#!/usr/bin/env python3
"""Execute original AArch64 route branch with external calls stubbed.
Checks CPU/control flow, NOT DSP behavior, HDMI transport or audible output.
"""
from pathlib import Path
import json, struct
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_X0, UC_ARM64_REG_X30, UC_ARM64_REG_SP, UC_ARM64_REG_PC
ROOT=Path(__file__).resolve().parents[3]
raw=(ROOT/'inputs/kernel.bin').read_bytes()
def run(bypass, active=False):
 u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);u.mem_map(0,0x5000000);u.mem_write(0,raw)
 def w(a,v,n=8):u.mem_write(a,v.to_bytes(n,'little'))
 g=0x25c4f70;out=0x3010000;node=0x3020000
 u.mem_write(g,b'\0'*0x600)
 w(g+8,0x3030000);w(g+0x20,node);w(node,g+0x20)
 w(node+0x14,1,4);w(node+0x18,1,4)
 w(g+0x1b4,1,4);w(g+0x1b8,1,4);w(g+0x19b,1,1)
 w(out+0x14,0x20,4);w(out+0x18,0x3040000)
 if active:
  w(out+0x31,1,1);w(out+0x30,1,1);w(out+0x34,0,4);w(out+0x38,0,1)
 w(g+0x4c+12,1,4);w(g+0x50+12,0,4)
 for i,v in enumerate([1,out,0,bypass,0]):u.reg_write(UC_ARM64_REG_X0+i,v)
 u.reg_write(UC_ARM64_REG_SP,0x4800000);u.reg_write(UC_ARM64_REG_X30,0x4900000)
 calls=[]
 def trace(uc,a,size,data):
  ins=struct.unpack('<I',bytes(uc.mem_read(a,4)))[0]
  if ins&0xfc000000 == 0x94000000:
   imm=ins&0x3ffffff
   if imm&0x2000000:imm-=0x4000000
   target=a+imm*4
   args=[uc.reg_read(UC_ARM64_REG_X0+i) for i in range(5)]
   calls.append({'target':hex(target),'args':args})
   uc.reg_write(UC_ARM64_REG_X0,0);uc.reg_write(UC_ARM64_REG_PC,a+4)
 u.hook_add(UC_HOOK_CODE,trace)
 u.emu_start(0xed5240,0x4900000,count=15000)
 assert u.reg_read(UC_ARM64_REG_PC)==0x4900000, 'did not return'
 return calls
positive=run(1);negative=run(0);active=run(1,True)
assert any(c['target']=='0xea0220' and c['args'][2]==256 for c in active)
assert any(c['target']=='0xeb3a00' and c['args'][4]==1 for c in positive)
assert any(c['target']=='0xe9ea90' and c['args'][1]==256 for c in positive)
assert any(c['target']=='0xea0220' and c['args'][2]==256 and c['args'][4]==256 for c in positive)
assert not any(c['target']=='0xea0220' and c['args'][2]==256 for c in negative)
report={'result':'PASS','scope':'Original CPU routing branch only; external calls stubbed',
        'bypass':positive,'ordinary':negative,'previously_active_pcm_route':active}
(ROOT/'build/reports/emulation.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: original kernel branch requests compressed port256 connections only when bypass is true')
