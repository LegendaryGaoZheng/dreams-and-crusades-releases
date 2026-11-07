"""Launch only the dev performance world, preserving normal PCL JVM flags.
Uses the latest PCL launch command solely as a read-only argument source.
No credentials or full launch command are written into results.
"""
from pathlib import Path
import ctypes, datetime, json, os, subprocess, sys
from perf_suite import require_idle
HERE=Path(__file__).resolve().parent
LIVE=Path(r'C:\Users\Legen\Desktop\游戏\.minecraft\versions\梦想与远征')
RELEASE=LIVE.with_name('梦想与远征_Release')
DEV=LIVE.parent/'梦想与远征_dev'
require_idle()
setup=json.loads((HERE/'perf'/'dev-20261104'/'setup.json').read_text(encoding='utf-8'))
WORLD=Path(setup['dev_world'])
assert WORLD.resolve().parent==(DEV/'saves').resolve() and WORLD.name=='perf_oldworld_20261103'
assert (WORLD/'level.dat').exists()
bat=(LIVE.parent.parent.parent/'PCL'/'LatestLaunch.bat')
# PCL sits under the game folder, beside .minecraft.
bat=Path(r'C:\Users\Legen\Desktop\游戏\PCL\LatestLaunch.bat')
text=bat.read_text(encoding='utf-8-sig')
line=next(s.strip() for s in text.splitlines() if 'java-runtime-epsilon' in s and ' -cp ' in s)
argc=ctypes.c_int();fn=ctypes.windll.shell32.CommandLineToArgvW
fn.restype=ctypes.POINTER(ctypes.c_wchar_p)
argv=fn(line,ctypes.byref(argc));args=[argv[i] for i in range(argc.value)]
ctypes.windll.kernel32.LocalFree(argv)
old=Path(args[args.index('--gameDir')+1])
assert old.resolve() in {LIVE.resolve(),RELEASE.resolve(),DEV.resolve(),(LIVE.parent/'dsh_five_test').resolve()}, 'Unknown PCL gameDir'
args=[s.replace(str(old),str(DEV)).replace('梦想与远征_Release.jar','梦想与远征_dev.jar').replace('梦想与远征.jar','梦想与远征_dev.jar') for s in args]
args[args.index('--gameDir')+1]=str(DEV)
args[args.index('--version')+1]='梦想与远征_dev'
for key in ('--quickPlaySingleplayer','--quickPlayMultiplayer','--quickPlayRealms'):
 while key in args:
  i=args.index(key);del args[i:i+2]
args+=['--quickPlaySingleplayer',WORLD.name]
# Use the ordinary pack's saved window dimensions, not a stale PCL default 854x480.
options=dict(s.split(':',1) for s in (HERE/'perf'/'dev-20261104'/'baseline'/'options.txt').read_text(encoding='utf-8').splitlines() if ':' in s)
for flag,key in (('--width','overrideWidth'),('--height','overrideHeight')):
 value=int(options.get(key,'0'))
 if value>0:
  if flag in args:args[args.index(flag)+1]=str(value)
  else:args.extend([flag,str(value)])
assert Path(args[args.index('--gameDir')+1]).resolve()==DEV.resolve()
assert not any(str(LIVE)+'\\' in s or str(LIVE)+'/' in s for s in args), 'Formal directory reference survived'
# Refuse changed runtime/JVM memory/GC flags between matrix arms; never persist auth args.
contract={'java':args[0],'flags':[s for s in args if s.startswith(('-XX:','-Xmx','-Xms','-Xss'))]}
contract_path=HERE/'perf'/'dev-20261104'/'jvm-contract.json'
if contract_path.exists():
 assert json.loads(contract_path.read_text(encoding='utf-8'))==contract, 'JVM flags changed between trials; start a new baseline revision'
else:contract_path.write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
run=HERE/'runs'/('dev-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));run.mkdir(parents=True)
pos=args.index('-cp');args[pos:pos]=['-XX:StartFlightRecording=filename='+run.name+'.jfr,settings=profile,dumponexit=true,maxsize=256m','-Xlog:gc*,safepoint:stdout:time,uptime,level,tags']
env=dict(os.environ)
for k in list(env):
 if k.upper() in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY'):env.pop(k,None)
with (run/'console.log').open('wb') as out:proc=subprocess.Popen(args,cwd=DEV,stdout=out,stderr=subprocess.STDOUT,env=env)
meta={'pid':proc.pid,'gameDir':str(DEV),'world':str(WORLD),'run':str(run),'started':datetime.datetime.now().isoformat(),'gc_flags':[s for s in args if s.startswith(('-XX:','-Xmx','-Xms'))]}
(HERE/'dev_test_process.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(meta,ensure_ascii=True),flush=True)
