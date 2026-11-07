"""Dev-only actual-world controlled measurements. No writes to the ordinary instance."""
from pathlib import Path
import argparse, json, math, re, shutil, subprocess, sys, time
from perf_suite import require_idle, save_json, java_processes, close_test, digest
HERE=Path(__file__).resolve().parent
ROOT=HERE/'perf'/'dev-20261104'
DEV=Path(r'C:\Users\Legen\Desktop\游戏\.minecraft\versions\梦想与远征_dev')
DIRS=('mods','config','kubejs','resourcepacks','shaderpacks')
WORLD=DEV/'saves'/'perf_oldworld_20261103'
PROBES=[DEV/'kubejs'/'startup_scripts'/'100_perf_measure.js',DEV/'kubejs'/'server_scripts'/'100_perf_route.js']
VIEWPORT={'width':1540,'height':692}
PHASES=('warmup','base','new','settle','loaded')


def check(condition,reason):
 if not condition:raise ValueError(str(reason))


def replace_allowed(target,source):
 target=target.resolve();allowed={(DEV/d).resolve() for d in DIRS}|{WORLD.resolve()}
 check(target in allowed and DEV.resolve() in target.parents,'Unapproved dev replacement '+str(target))
 print('Verified dev-only replacement target:',target,flush=True)
 if target.exists():shutil.rmtree(target)
 shutil.copytree(source,target)


def reject_lanserverproperties(mods):
 check(mods.is_dir(),'Missing mods directory: '+str(mods))
 forbidden=[str(p) for p in mods.rglob('*') if p.is_file() and p.name.lower().startswith('lanserverproperties') and '.jar' in p.name.lower()]
 check(not forbidden,'Refuse lanserverproperties jar (including disabled copies): '+str(forbidden))


def restore_world():
 setup=json.loads((ROOT/'setup.json').read_text(encoding='utf-8'))
 replace_allowed(WORLD,Path(setup['immutable_world']))
 sys.path.insert(0,str(HERE.parent/'_struct'))
 import nbt, nbt_typed
 level=nbt_typed.load(str(WORLD/'level.dat'));level.value['Data'].value['LevelName']=nbt.Str('梦想与远征 · 正式地图测试副本')
 nbt.save(level.value,str(WORLD/'level.dat'))


def prepare(on,pilot,spark_background=True,rep=1,flywheel_workers=None):
 require_idle();setup=json.loads((ROOT/'setup.json').read_text(encoding='utf-8'))
 check(Path(setup['dev_world']).resolve()==WORLD.resolve(),'Unexpected dev world')
 # Refuse before touching any runtime directory, then verify the copied mods too.
 reject_lanserverproperties(ROOT/'baseline'/'mods')
 for d in DIRS:replace_allowed(DEV/d,ROOT/'baseline'/d)
 reject_lanserverproperties(DEV/'mods')
 shutil.copy2(ROOT/'baseline'/'options.txt',DEV/'options.txt')
 opt=DEV/'options.txt';text=opt.read_text(encoding='utf-8').replace('pauseOnLostFocus:true','pauseOnLostFocus:false');opt.write_text(text,encoding='utf-8')
 off=DEV/'mods'/'iris-flywheel-compat-NeoForge-2.4.0.jar.off'
 if on:
  check(off.exists(),'Missing disabled irisflw baseline');print('Verified dev-only rename source:',off.resolve(),flush=True);off.rename(off.with_suffix(''))
 reject_lanserverproperties(DEV/'mods')
 restore_world()
 spark=DEV/'config'/'spark'/'config.json'
 spark_config=json.loads(spark.read_text(encoding='utf-8'));spark_config['backgroundProfiler']=spark_background;save_json(spark,spark_config)
 cfg={'spark_background':spark_background,'probe_version':3,'rep':rep,'scene_note':'base means saved player position; not yet verified as machine-heavy base','test_only':True,'source':'dev_actual_map','irisflw':on,'pilot':pilot,'clock':'KubeJS Utils.getSystemTime millisecond resolution','warmup_seconds':15 if pilot else 60,'phase_seconds':20 if pilot else 120,'settle_seconds':5 if pilot else 20,'hops':3 if pilot else 30,'hop_interval_ms':2000 if pilot else 2500,'route_x':12000,'route_y':160,'route_z':12000,'step':32}
 if flywheel_workers is not None:
  check(type(flywheel_workers) is int and -1<=flywheel_workers<=20,'Invalid Flywheel worker count')
  flywheel=DEV/'config'/'flywheel-client.toml'
  check(flywheel.resolve().parent==(DEV/'config').resolve(),'Unexpected Flywheel configuration target')
  before=flywheel.read_text(encoding='utf-8')
  after,count=re.subn(r'(?m)^(workerThreads[ \t]*=[ \t]*)-?\d+([ \t]*)$',lambda m:m[1]+str(flywheel_workers)+m[2],before)
  check(count==1,'Expected exactly one Flywheel workerThreads setting')
  flywheel.write_text(after,encoding='utf-8')
  cfg['flywheel_worker_threads']=flywheel_workers
  print('Dev-only Flywheel workers override:',flywheel.resolve(),flywheel_workers,flush=True)
 save_json(DEV/'config'/'dsh_perf_run.json',cfg)
 # A previous baseline result must never satisfy this run's completion markers.
 for name in ('dsh_perf_result.json',):
  stale=DEV/'config'/name
  if stale.exists():stale.unlink()
 for p in PROBES:shutil.copy2(HERE/'perf'/p.name,p)
 return cfg


def source_probe_hashes():
 return {str(p):digest(HERE/'perf'/p.name) for p in PROBES}


def clean_probes(expected_hashes=None):
 # With no argument retain pause/manual-cleanup compatibility. During a run use
 # the prelaunch hashes, not source files another agent may subsequently edit.
 expected=source_probe_hashes() if expected_hashes is None else expected_hashes
 for p in PROBES:
  check(p.resolve().parent in {(DEV/'kubejs'/'startup_scripts').resolve(),(DEV/'kubejs'/'server_scripts').resolve()},'Unapproved probe cleanup')
  if p.exists():
   check(digest(p)==expected[str(p)],'Installed probe changed, refuse deletion: '+str(p))
   print('Verified temporary dev probe cleanup:',p.resolve(),flush=True);p.unlink()


class LogTail:
 """Read only newly appended bytes; keep markers, not the whole console log."""
 def __init__(self,path):
  self.path=path;self.offset=0;self.pending=b'';self.complete=False;self.route_complete=False;self.failure=None;self.viewports=[]
 def poll(self,final=False,closing=False):
  if not self.path.exists():return
  if self.path.stat().st_size<self.offset:
   self.offset=0;self.pending=b'';self.failure='Console log was truncated during measurement'
  with self.path.open('rb') as stream:
   stream.seek(self.offset)
   while True:
    block=stream.read(65536)
    if not block:break
    self.offset+=len(block);lines=(self.pending+block).split(b'\n');self.pending=lines.pop()
    for line in lines:self.consume(line.decode('utf-8',errors='replace'),closing)
  if final and self.pending:
   self.consume(self.pending.decode('utf-8',errors='replace'),closing);self.pending=b''
 def consume(self,line,closing=False):
  lower=line.lower()
  fatal=('unreported exception thrown!', 'exception caught during firing event', 'startup script errors',
         'preparing crash report', '[perf2] failed ', '[perf2] route_failed ',
         'error loading kubejs script', 'error loading script', 'error executing script',
         'error in startup script', 'failed to load startup script')
  startup_error=('startup_scripts' in lower or 'startup script' in lower) and any(x in lower for x in ('[error]', '/error]', ' error ', 'exception', 'syntaxerror', 'referenceerror', 'typeerror'))
  # Even after completion, an event-handler/startup crash invalidates the run.
  if any(token in lower for token in fatal) or startup_error or ('stopping!' in lower and not closing):
   if self.failure is None:self.failure='Console failure: '+line.strip()[:1000]
  if '[PERF2]' in line:print(line,flush=True)
  if '[PERF2] COMPLETE ' in line:self.complete=True
  if '[PERF2] ROUTE_COMPLETE ' in line:self.route_complete=True
  marker='[PERF2] VIEWPORT '
  if marker in line:
   try:
    viewport=json.JSONDecoder().raw_decode(line.split(marker,1)[1].strip())[0]
    self.viewports.append(viewport)
    if viewport!=VIEWPORT:self.failure='Resolution changed/unexpected viewport: '+str(viewport)
   except (ValueError,TypeError):self.failure='Malformed viewport marker'


def validate(result,cfg):
 check(not result.get('failed'),result.get('reason','Probe reported failure'))
 check(result['run']==cfg,'Actual game config differs from perf-config (including rep/probe_version)')
 check(result['viewport']==VIEWPORT,'Unexpected measured resolution')
 for viewport in result.get('viewports',[]):check(viewport==VIEWPORT,'Resolution changed during measurement')
 check(not result.get('viewport_changes'),'Resolution changed during measurement')
 summaries=result['summaries']
 check(len(summaries)==len(PHASES),'Unexpected phase summary count')
 frames=result['frames'];counts={phase:0 for phase in PHASES}
 for row in frames:
  check(len(row)>=4 and row[0] in counts,'Unexpected frame row/phase')
  check(isinstance(row[2],(int,float)) and math.isfinite(row[2]) and row[2]>0,'Invalid frame duration')
  counts[row[0]]+=1
 for phase in PHASES:
  rows=[s for s in summaries if s['phase']==phase]
  check(len(rows)==1 and rows[0]['frames']>10 and not rows[0].get('invalid'),('missing/empty phase',phase))
  check(rows[0]['frames']==counts[phase],('frame/summary count mismatch',phase))
 route=result['route'];check(len(route)==2*(cfg['hops']+1),('route count',len(route)))
 for phase in ('new','loaded'):
  rows=[r for r in route if r['phase']==phase]
  check([r['hop'] for r in rows]==list(range(cfg['hops']+1)),('route hops',phase))
  for r in rows:
   for axis,expected in (('x',cfg['route_x']+r['hop']*cfg['step']),('y',cfg['route_y']),('z',cfg['route_z'])):
    check(isinstance(r[axis],(int,float)) and math.isfinite(r[axis]) and abs(r[axis]-expected)<.1,('route coordinate',phase,r['hop'],axis,r[axis],expected))


def validate_jfr(path):
 # A dumponexit message is not evidence that the recording actually exists or
 # is complete. Check every chunk boundary; do not infer performance benefit.
 check(path.is_file(),'Missing JFR recording: '+str(path))
 size=path.stat().st_size;check(size>68,'Empty/truncated JFR recording')
 with path.open('rb') as stream:
  offset=0
  while offset<size:
   stream.seek(offset);header=stream.read(68)
   check(len(header)==68 and header[:4]==b'FLR\x00','Invalid/truncated JFR header')
   chunk=int.from_bytes(header[8:16],'big')
   check(chunk>68 and offset+chunk<=size,'Incomplete JFR chunk')
   offset+=chunk
  check(offset==size,'Trailing incomplete JFR data')


def run(on,pilot,rep,spark_background=True,flywheel_workers=None,timeout_seconds=None):
 # Always leave a validation artifact, even when prepare/launch/metadata fails.
 run_dir=ROOT/'runner-attempts'/str(time.time_ns());cfg=None;pid=None;tail=None;expected_hashes=None
 success=False;reason='Run did not reach complete validation';errors=[];completed=False;result=None;owned_exited=True
 def failure(message):
  nonlocal reason
  message=str(message);errors.append(message)
  if len(errors)==1:reason=message
 try:
  expected_hashes=source_probe_hashes()
  cfg=prepare(on,pilot,spark_background,rep=rep,flywheel_workers=flywheel_workers)
  for p in PROBES:check(digest(p)==expected_hashes[str(p)],'Probe source changed during preparation')
  # Save the source identity before launching; cleanup never hashes live source.
  save_json(run_dir/'probe-hashes.json',expected_hashes)
  require_idle()
  meta_file=HERE/'dev_test_process.json'
  old_meta=meta_file.read_bytes() if meta_file.exists() else None
  subprocess.run([sys.executable,str(HERE/'launch_dev_perf.py')],check=True)
  check(meta_file.exists() and meta_file.read_bytes()!=old_meta,'Launcher did not publish fresh owned-process metadata')
  meta=json.loads(meta_file.read_text(encoding='utf-8'))
  check(Path(meta['gameDir']).resolve()==DEV.resolve() and Path(meta['world']).resolve()==WORLD.resolve(),'Unapproved launch metadata; refuse to close unknown PID')
  actual_run=Path(meta['run']).resolve()
  check(actual_run.parent==(HERE/'runs').resolve() and actual_run.name.startswith('dev-'),'Unapproved launch run directory')
  check(type(meta['pid']) is int and meta['pid']>0,'Invalid owned PID')
  pid=meta['pid'];run_dir=actual_run
  save_json(run_dir/'perf-config.json',cfg);save_json(run_dir/'probe-hashes.json',expected_hashes)
  timeout=(350 if pilot else 1100) if timeout_seconds is None else timeout_seconds;check(0<timeout<=1100,'Invalid runner timeout');end=time.monotonic()+timeout;tail=LogTail(run_dir/'console.log')
  while time.monotonic()<end:
   tail.poll()
   if tail.failure:raise ValueError(tail.failure)
   processes=java_processes();extra=[p for p in processes if p[0]!=pid]
   check(not extra,'Additional Java process detected (will not close it): '+str(extra))
   check(any(p[0]==pid for p in processes),'Owned game process exited before validation')
   if tail.complete and tail.route_complete:
    result_file=DEV/'config'/'dsh_perf_result.json'
    check(result_file.is_file(),'Completion markers without route/result file')
    result=json.loads(result_file.read_text(encoding='utf-8'));validate(result,cfg)
    completed=True;break
   time.sleep(.5)
  else:raise TimeoutError('Total timeout after '+str(timeout)+'s; COMPLETE='+str(tail.complete)+', ROUTE_COMPLETE='+str(tail.route_complete))
 except Exception as exc:
  failure(type(exc).__name__+': '+str(exc))
 finally:
  # Only the fresh launcher metadata PID is owned. Never close extra Java PIDs.
  if pid is not None:
   try:
    if any(p[0]==pid for p in java_processes()):
     try:subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(HERE/'game_ui.ps1'),'-MetaFile',str(HERE/'dev_test_process.json'),'-Action','capture','-Out',str(run_dir/'scene-final.png')],timeout=20,check=False)
     except Exception as exc:failure('Final capture failed: '+str(exc))
     finally:close_test(pid)
    deadline=time.monotonic()+60
    while time.monotonic()<deadline and any(p[0]==pid for p in java_processes()):time.sleep(.5)
    owned_exited=not any(p[0]==pid for p in java_processes())
    check(owned_exited,'Owned dev game did not close; runtime left untouched')
   except Exception as exc:
    owned_exited=False;failure('Owned-process cleanup failed: '+str(exc))
  try:
   processes=java_processes()
   check(not processes,'Java still active; refuse runtime probe cleanup (no unknown PID will be closed): '+str(processes))
   if expected_hashes is not None:clean_probes(expected_hashes)
  except Exception as exc:failure('Probe cleanup failed: '+str(exc))
  # Read final output and copy artifacts only after shutdown/cleanup so buffers
  # and dumponexit recording have been flushed. Failure must not skip validation.
  if tail is not None:
   try:
    tail.poll(final=True,closing=True)
    if tail.failure and tail.failure not in errors:failure(tail.failure)
   except Exception as exc:failure('Final console read failed: '+str(exc))
  artifacts=[(DEV/'config'/'dsh_perf_result.json','perf-result.json'),
             (DEV/'logs'/'latest.log','acceptance-latest.log')]
  if pid is not None:artifacts.append((run_dir/'console.log','acceptance-console.log'))
  for source,name in artifacts:
   try:
    if source.exists():shutil.copy2(source,run_dir/name)
   except Exception as exc:failure('Artifact copy failed ('+name+'): '+str(exc))
  if pid is not None:
   try:
    recording=DEV/(run_dir.name+'.jfr')
    if recording.exists():shutil.copy2(recording,run_dir/'profile.jfr')
    check(owned_exited,'Cannot validate a recording while owned game is still running')
    validate_jfr(run_dir/'profile.jfr')
   except Exception as exc:failure('JFR validation failed: '+str(exc))
  if completed:
   try:
    # Recheck the final on-disk result, not just the first completion snapshot.
    final_result=run_dir/'perf-result.json';check(final_result.is_file(),'Missing final route/result artifact')
    validate(json.loads(final_result.read_text(encoding='utf-8')),cfg)
    if 'flywheel_worker_threads' in cfg:
     observed=re.findall(r'(?m)^workerThreads[ \t]*=[ \t]*(-?\d+)[ \t]*$',(DEV/'config'/'flywheel-client.toml').read_text(encoding='utf-8'))
     check(observed==[str(cfg['flywheel_worker_threads'])],'Flywheel worker override changed/rejected by game')
   except Exception as exc:failure('Final result validation failed: '+str(exc))
  success=completed and not errors and owned_exited
  if success:reason='Route, phases, frame counts, XYZ/hops, config, resolution and JFR structure validated; no performance-benefit conclusion'
  save_json(run_dir/'validation.json',{'success':success,'reason':reason,'errors':errors,'pilot':pilot,'config':cfg,'owned_pid':pid,'owned_exited':owned_exited,'performance_conclusion':False})
 print('DEV_RUN_FINISHED',str(run_dir),'success',success,reason,flush=True)
 if not success:raise RuntimeError('Invalid pilot/measurement; inspect validation/log; no performance conclusion allowed: '+reason)


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--irisflw',choices=['on','off'],default='off');p.add_argument('--pilot',action='store_true');p.add_argument('--rep',type=int,default=1);p.add_argument('--spark-background',choices=['on','off'],default='on');p.add_argument('--flywheel-workers',type=int,choices=range(-1,21),default=None);a=p.parse_args()
 run(a.irisflw=='on',a.pilot,a.rep,a.spark_background=='on',flywheel_workers=a.flywheel_workers)
