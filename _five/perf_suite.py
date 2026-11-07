"""Ordinary-pack controlled tests. Only writes baseline artifacts and dsh_five_test.
Never launches or mutates the ordinary/dev game directories or their saves.
"""
from pathlib import Path
import argparse, ctypes, datetime, hashlib, json, shutil, subprocess, sys, time
from ctypes import wintypes as w
HERE=Path(__file__).resolve().parent
LIVE=Path(r'C:\Users\Legen\Desktop\游戏\.minecraft\versions\梦想与远征')
TEST=LIVE.parent/'dsh_five_test'
ROOT=HERE/'perf'/'ordinary-20261103'
BASE=ROOT/'baseline'
PACK_DIRS=('mods','config','kubejs','resourcepacks','shaderpacks')
PYTHON=sys.executable

def java_processes():
 class ENTRY(ctypes.Structure):
  _fields_=[('dwSize',w.DWORD),('cntUsage',w.DWORD),('pid',w.DWORD),('heap',ctypes.c_size_t),('module',w.DWORD),('threads',w.DWORD),('parent',w.DWORD),('priority',w.LONG),('flags',w.DWORD),('exe',w.WCHAR*260)]
 k=ctypes.WinDLL('kernel32',use_last_error=True)
 k.CreateToolhelp32Snapshot.argtypes=[w.DWORD,w.DWORD];k.CreateToolhelp32Snapshot.restype=w.HANDLE
 k.Process32FirstW.argtypes=[w.HANDLE,ctypes.POINTER(ENTRY)];k.Process32NextW.argtypes=[w.HANDLE,ctypes.POINTER(ENTRY)];k.CloseHandle.argtypes=[w.HANDLE]
 h=k.CreateToolhelp32Snapshot(2,0);e=ENTRY();e.dwSize=ctypes.sizeof(ENTRY);out=[]
 try:
  good=k.Process32FirstW(h,ctypes.byref(e))
  while good:
   if e.exe.lower() in ('java.exe','javaw.exe'):out.append((e.pid,e.exe))
   good=k.Process32NextW(h,ctypes.byref(e))
 finally:k.CloseHandle(h)
 return out

def require_idle():
 running=java_processes()
 if running:raise RuntimeError('Java process active; do not overwrite running game: '+str(running))

def save_json(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def safe_remove_test(p):
 p=p.resolve();allowed={*( (TEST/d).resolve() for d in PACK_DIRS),(TEST/'saves'/'five_perf').resolve()}
 if p not in allowed or TEST.resolve() not in p.parents:raise RuntimeError('Unapproved deletion '+str(p))
 print('Verified isolated replacement target:',p,flush=True)
 if p.exists():shutil.rmtree(p)

def snapshot():
 require_idle()
 if BASE.exists():raise RuntimeError('Snapshot already exists; never overwrite baseline')
 BASE.mkdir(parents=True)
 for d in PACK_DIRS:shutil.copytree(LIVE/d,BASE/d)
 for name in ('options.txt','梦想与远征.jar','梦想与远征.json'):
  shutil.copy2(LIVE/name,BASE/name)
 shutil.copytree(LIVE/'saves'/'oldworld',BASE/'world')
 require_idle()
 manifest={str(p.relative_to(BASE)).replace('\\','/'):{'bytes':p.stat().st_size,'sha256':digest(p)} for p in BASE.rglob('*') if p.is_file()}
 save_json(ROOT/'baseline-manifest.json',{'source':str(LIVE),'save':'oldworld','created':datetime.datetime.now().isoformat(),'files':manifest})
 print('SNAPSHOT_COMPLETE',len(manifest),'files',sum(x['bytes'] for x in manifest.values()),flush=True)

def prepare(on,pilot):
 require_idle()
 if not (ROOT/'baseline-manifest.json').exists():raise RuntimeError('No completed snapshot')
 archive=ROOT/'previous-test-config'
 if not archive.exists():
  archive.mkdir()
  for d in PACK_DIRS:
   if (TEST/d).exists():shutil.copytree(TEST/d,archive/d)
  if (TEST/'options.txt').exists():shutil.copy2(TEST/'options.txt',archive/'options.txt')
 for d in PACK_DIRS:
  safe_remove_test(TEST/d);shutil.copytree(BASE/d,TEST/d)
 for name in ('options.txt','梦想与远征.jar','梦想与远征.json'):shutil.copy2(BASE/name,TEST/name)
 opt=TEST/'options.txt';text=opt.read_text(encoding='utf-8');text=text.replace('pauseOnLostFocus:true','pauseOnLostFocus:false');opt.write_text(text,encoding='utf-8')
 # Both arms derive identical mods from the ordinary pack, only this suffix differs.
 off=TEST/'mods'/'iris-flywheel-compat-NeoForge-2.4.0.jar.off';enabled=off.with_suffix('')
 if on:
  if not off.exists():raise RuntimeError('Expected ordinary disabled irisflw baseline')
  print('Verified isolated rename source:',off.resolve(),flush=True);off.rename(enabled)
 world=TEST/'saves'/'five_perf';safe_remove_test(world);shutil.copytree(BASE/'world',world)
 cfg={'test_only':True,'source':'ordinary','irisflw':on,'pilot':pilot,'warmup_seconds':15 if pilot else 60,'phase_seconds':20 if pilot else 120,'settle_seconds':5 if pilot else 20,'hops':3 if pilot else 30,'hop_interval_ms':2000 if pilot else 2500,'route_x':12000,'route_y':160,'route_z':12000,'step':32}
 save_json(TEST/'config'/'dsh_perf_run.json',cfg)
 shutil.copy2(HERE/'perf'/'100_perf_measure.js',TEST/'kubejs'/'startup_scripts'/'100_perf_measure.js')
 shutil.copy2(HERE/'perf'/'100_perf_route.js',TEST/'kubejs'/'server_scripts'/'100_perf_route.js')
 # Audit that no old automated scene scripts survived the ordinary snapshot.
 scripts=[str(p.relative_to(TEST)) for p in (TEST/'kubejs').rglob('*.js')]
 assert not any('99_five_frame_probe' in s or '92_chunk_fly' in s for s in scripts)
 print('PREPARED',json.dumps(cfg),flush=True)

def close_test(pid):
 u=ctypes.WinDLL('user32',use_last_error=True);cb=ctypes.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
 u.GetWindowThreadProcessId.argtypes=[w.HWND,ctypes.POINTER(w.DWORD)];u.PostMessageW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM]
 def stop(h,p):
  owner=w.DWORD();u.GetWindowThreadProcessId(h,ctypes.byref(owner))
  if owner.value==pid:u.PostMessageW(h,0x10,0,0)
  return True
 u.EnumWindows(cb(stop),0)

def run(on,pilot,rep):
 prepare(on,pilot)
 subprocess.run([PYTHON,str(HERE/'launch_test.py'),'--world','five_perf','--profile'],check=True)
 meta=json.loads((HERE/'test_process.json').read_text(encoding='utf-8'));run_dir=Path(meta['run']);pid=meta['pid']
 cfg=json.loads((TEST/'config'/'dsh_perf_run.json').read_text(encoding='utf-8'));cfg['rep']=rep;save_json(run_dir/'perf-config.json',cfg)
 end=time.monotonic()+(330 if pilot else 1000);log=run_dir/'console.log';last_size=0;success=False;seen=set()
 try:
  while time.monotonic()<end:
   if log.exists() and log.stat().st_size!=last_size:
    last_size=log.stat().st_size;text=log.read_text(encoding='utf-8',errors='replace')
    for line in text.splitlines():
     if '[PERF2]' in line and line not in seen:
      seen.add(line);print(line,flush=True)
    if '[PERF2] COMPLETE ' in text:
     success='[PERF2] ROUTE_COMPLETE ' in text;break
    if '[PERF2] FAILED ' in text or '[PERF2] ROUTE_FAILED ' in text or 'Preparing crash report' in text or 'Stopping!' in text:break
   if not any(p[0]==pid for p in java_processes()):break
   time.sleep(.5)
 finally:
  result=TEST/'config'/'dsh_perf_result.json'
  if result.exists():shutil.copy2(result,run_dir/'perf-result.json')
  latest=TEST/'logs'/'latest.log'
  if latest.exists():shutil.copy2(latest,run_dir/'acceptance-latest.log')
  # Capture only the isolated window, never foreground or type into user's apps.
  try:subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(HERE/'game_ui.ps1'),'-Action','capture','-Out',str(run_dir/'scene-final.png')],timeout=20,check=False)
  finally:close_test(pid)
  deadline=time.monotonic()+45
  while time.monotonic()<deadline and any(p[0]==pid for p in java_processes()):time.sleep(.5)
  if any(p[0]==pid for p in java_processes()):raise RuntimeError('Isolated game did not close; not killing unknown state')
 recording=TEST/('perf-'+run_dir.name+'.jfr')
 if recording.exists():shutil.copy2(recording,run_dir/'profile.jfr')
 save_json(run_dir/'validation.json',{'success':success,'pilot':pilot,'config':cfg})
 print('RUN_FINISHED',run_dir,'success',success,flush=True)
 if not success:raise RuntimeError('Invalid measurement; inspect run log')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['snapshot','run']);p.add_argument('--irisflw',choices=['on','off'],default='off');p.add_argument('--pilot',action='store_true');p.add_argument('--rep',type=int,default=1);a=p.parse_args()
 if a.action=='snapshot':snapshot()
 else:run(a.irisflw=='on',a.pilot,a.rep)
