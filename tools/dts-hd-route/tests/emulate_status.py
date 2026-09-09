from pathlib import Path
import struct,json
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_X0 as X0,UC_ARM64_REG_X30 as LR,UC_ARM64_REG_SP as SP,UC_ARM64_REG_PC as PC
root=Path(__file__).resolve().parents[3]
raw=(root/'inputs/kernel.bin').read_bytes()
def run(codec,patched,outtype=3):
 u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);u.mem_map(0,0x5000000);u.mem_write(0,raw)
 def w(a,v,n=4):u.mem_write(a,v.to_bytes(n,'little'))
 event=0x3010000;out=0x3020000;name=0x3030000
 for i,v in enumerate([codec,8,192000,0]):w(event+4*i,v)
 w(out+0x2c,outtype);w(out+0x81,1,1)
 u.mem_write(name,b'dts-hd\0')
 for i,v in enumerate([event,16,out]):u.reg_write(X0+i,v)
 u.reg_write(SP,0x4800000);u.reg_write(LR,0x4900000)
 calls=[]
 def hook(uc,a,size,data):
  if patched and a==0xeb356c and uc.reg_read(X0+6)==7 and outtype==3:
   uc.reg_write(PC,0xeb366c);return
  if patched and a==0xeb362c and uc.reg_read(X0+4)>5:
   uc.reg_write(X0+7,name);uc.reg_write(PC,a+4);return
  ins=int.from_bytes(uc.mem_read(a,4),'little')
  if ins&0xfc000000==0x94000000:
   off=ins&0x3ffffff
   if off&0x2000000:off-=0x4000000
   calls.append({'target':hex(a+off*4),'args':[uc.reg_read(X0+i) for i in range(8)]})
   uc.reg_write(X0,0);uc.reg_write(PC,a+4)
 u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0xeb3524,0x4900000,count=2000)
 assert u.reg_read(PC)==0x4900000
 return calls
baseline=run(7,False);fixed=run(7,True)
assert any(c['target']=='0xeb2e64' and c['args'][1]==0 for c in baseline)
assert any(c['target']=='0xd9c440' and c['args'][7]==0x6d756c6f765f7465 for c in baseline)
assert any(c['target']=='0xeb2e64' and c['args'][1]==7 for c in fixed)
assert any(c['target']=='0xd9c440' and c['args'][7]==0x3030000 for c in fixed)
for codec in range(5):assert run(codec,False)==run(codec,True)
assert any(c['target']=='0xeb2e64' and c['args'][1]==0 for c in run(7,True,2))
(root/'build/reports/status-emulation.json').write_text(json.dumps({'status':'PASS','scope':'CPU callback branch; external functions stubbed','baseline':baseline,'fixed':fixed},indent=2)+'\n')
print('PASS: reproduces bad log pointer/PCM fallback; fixes codec7; codecs0..4 unchanged; optical excluded')
