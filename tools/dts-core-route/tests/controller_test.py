#!/usr/bin/env python3
"""Exercise shell lifecycle with a fake /proc tree and fake TV commands.
No SSH, real modules, or device access. Does not simulate DSP property semantics.
"""
import os, subprocess, tempfile, pathlib, json
R=pathlib.Path(__file__).resolve().parents[3]
source=(R/'tools/dts-core-route/run-on-tv.sh').read_text()
results=[]
for case in ('success','bad_input','gate_fail','route_fail','missing_graph','source_change','unload_fail','missing_gain'):
 with tempfile.TemporaryDirectory(prefix='dts-controller-') as tmp:
  d=pathlib.Path(tmp);proc=d/'proc';bin=d/'bin';bin.mkdir()
  audio=proc/'lgtv-driver/audio';audio.mkdir(parents=True)
  (audio/'hdmi').write_text('Codec='+('PCM' if case=='bad_input' else 'DTS')+'\nSamplingRate=48000\nAudioData=1\n')
  (audio/'adec.p1').write_text('Connect=HDMI_PORT2\nUserCodec=DTS\nStart=1\n')
  (audio/'sndout').write_text('EArcOnOff=On\n')
  inst=proc/'aaudio/processors/dsp0/hdmi1/021c0003';inst.mkdir(parents=True)
  (inst/'prop').write_text('hdmi-port=(int)2\ncodec=(int)0\nmode=(int)1\ndata-drop-mode=(int)2\ndrop-output-data=(bool)true\ndrop=(bool)true\nstart=(int)0\n')
  gain=proc/'aaudio/processors/dsp2/gain/041b0001';gain.mkdir(parents=True)
  (gain/'prop').write_text('mute-input=(bool)true\nmute-output=(bool)true\n')
  (proc/'aaudio/dot_module_connection').write_text('' if case=='missing_gain' else ' gain_041b0001_test -> bypass_04160001_test;\n')
  (inst/'lstatus').write_text('ES data type : 11\n')
  graph='renderer_1_out100 -> mixer_0_in100\nmixer_0_out100 -> output_3_in0\n'
  (proc/'aaudio/dot_block_connection').write_text('' if case=='missing_graph' else graph)
  mock='''#!/usr/bin/env python3
import os,sys,pathlib
D=pathlib.Path(os.environ['FIXTURE']);C=os.environ['CASE'];n=pathlib.Path(sys.argv[0]).name
with (D/'commands').open('a') as f:f.write(n+' '+ ' '.join(sys.argv[1:])+'\\n')
if n=='id':print('0')
elif n=='uname':print('5.4.268-329.ptl4tv.5')
elif n=='sha256sum':pass
elif n=='lsmod':pass
elif n=='insmod':
 if (C=='gate_fail' and 'dts_gate.ko' in sys.argv[1]) or (C=='route_fail' and 'dts_core_route.ko' in sys.argv[1]):sys.exit(1)
elif n=='rmmod':
 if C=='unload_fail' and sys.argv[1]=='dts_core_route':sys.exit(1)
elif n=='amixer':print('  : values=2,1,0,0,1')
elif n=='dmesg':print('dts_gate: restore result=0\\ndts_core_route: unloaded')
elif n=='sleep':
 if C=='source_change':(D/'proc/lgtv-driver/audio/hdmi').write_text('Codec=PCM\\nSamplingRate=48000\\n')
'''
  for name in ('id','uname','sha256sum','lsmod','insmod','rmmod','amixer','dmesg','sleep','systemctl'):
   p=bin/name;p.write_text(mock);p.chmod(0o755)
  # Redirect only filesystem literals in the test copy, not the deliverable.
  script=source.replace('/proc/',str(proc)+'/').replace('/tmp/dts-core-test-',str(d)+'/log-')
  (d/'run.sh').write_text(script)
  env={**os.environ,'PATH':str(bin)+':'+os.environ['PATH'],'FIXTURE':str(d),'CASE':case}
  r=subprocess.run(['sh',str(d/'run.sh'),'--apply','15'],env=env,capture_output=True,text=True,timeout=15)
  calls=(d/'commands').read_text()
  if case=='success':assert r.returncode==0,(case,r.stdout,r.stderr)
  else:assert r.returncode!=0,(case,r.stdout,r.stderr)
  if case=='bad_input':assert 'insmod' not in calls
  if case not in ('bad_input','gate_fail'):assert 'rmmod dts_gate' in calls
  if case in ('success','missing_graph','source_change','unload_fail','missing_gain'):assert 'rmmod dts_core_route' in calls
  if case=='route_fail':assert 'rmmod dts_core_route' not in calls
  if case=='unload_fail':assert 'Rollback incomplete' in r.stdout
  results.append({'case':case,'result':'PASS','exit_code':r.returncode})
(R/'build/reports/core-controller-tests.json').write_text(json.dumps(results,indent=2)+'\n')
print('PASS:',len(results),'controller lifecycle scenarios (mock devices only)')
