"""Set up dev-only workflow and a verified copy of the current ordinary world."""
from pathlib import Path
import datetime, hashlib, json, shutil, sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from perf_suite import require_idle, digest, save_json
HERE=Path(__file__).resolve().parent
LIVE=Path(r'C:\Users\Legen\Desktop\游戏\.minecraft\versions\梦想与远征')
DEV=LIVE.parent/'梦想与远征_dev'
ROOT=HERE/'perf'/'dev-20261103'
WORLD=DEV/'saves'/'perf_oldworld_20261103'
DIRS=('mods','config','kubejs','resourcepacks','shaderpacks')

def manifest(folder):
 return {str(p.relative_to(folder)).replace('\\','/'):{'bytes':p.stat().st_size,'sha256':digest(p)} for p in folder.rglob('*') if p.is_file()}

def main():
 require_idle()
 if ROOT.exists() or WORLD.exists():raise RuntimeError('Existing setup/world: refuse overwrite')
 ROOT.mkdir(parents=True)
 source=LIVE/'saves'/'oldworld'
 before=manifest(source)
 shutil.copytree(source,WORLD)
 copied=manifest(WORLD);after=manifest(source)
 if before!=after or before!=copied:raise RuntimeError('Source changed or copy verification failed')
 require_idle()
 old=HERE/'perf'/'ordinary-20261103'/'baseline'/'world'
 if old.exists() and manifest(old)==before:
  immutable=old;print('Reusing verified identical immutable world snapshot; no additional 2.7GB copy',flush=True)
 else:
  immutable=ROOT/'world-snapshot';shutil.copytree(WORLD,immutable)
  assert manifest(immutable)==before
 # Preserve the existing dev runtime before establishing the formal pack as test baseline.
 backup=ROOT/'dev-before';backup.mkdir()
 baseline=ROOT/'baseline';baseline.mkdir()
 for d in DIRS:
  if (DEV/d).exists():shutil.copytree(DEV/d,backup/d)
  shutil.copytree(LIVE/d,baseline/d)
 if (DEV/'options.txt').exists():shutil.copy2(DEV/'options.txt',backup/'options.txt')
 shutil.copy2(LIVE/'options.txt',baseline/'options.txt')
 runtime_before={d:manifest(LIVE/d) for d in DIRS}
 for d in DIRS:
  target=(DEV/d).resolve()
  assert target.parent==DEV.resolve() and target.name in DIRS
  print('Verified dev runtime replacement target:',target,flush=True)
  if target.exists():shutil.rmtree(target)
  shutil.copytree(baseline/d,target)
 shutil.copy2(baseline/'options.txt',DEV/'options.txt')
 # Restore a type-preserving NBT copy, modifying only the display name in dev.
 sys.path.insert(0,str(HERE.parent/'_struct'))
 import nbt, nbt_typed
 level=nbt_typed.load(str(WORLD/'level.dat'))
 old_title=level.value['Data'].value['LevelName'].value
 level.value['Data'].value['LevelName']=nbt.Str('梦想与远征 · 正式地图测试副本')
 nbt.save(level.value,str(WORLD/'level.dat'))
 require_idle()
 if manifest(source)!=before:raise RuntimeError('Formal world changed during setup')
 if {d:manifest(LIVE/d) for d in DIRS}!=runtime_before:raise RuntimeError('Formal runtime changed during setup')
 save_json(ROOT/'setup.json',{'created':datetime.datetime.now().isoformat(),'live':str(LIVE),'dev':str(DEV),'source_world':str(source),'dev_world':str(WORLD),'immutable_world':str(immutable),'original_title':old_title,'copy_verified':True,'files':len(before),'bytes':sum(x['bytes'] for x in before.values()),'only_dev_world_change':'level.dat Data.LevelName','source_manifest':before,'runtime_manifest':runtime_before})
 print('DEV_SETUP_COMPLETE',json.dumps({'world':str(WORLD),'files':len(before),'bytes':sum(x['bytes'] for x in before.values()),'formal_unchanged':True},ensure_ascii=True),flush=True)
def finish_existing():
 require_idle()
 if (ROOT/'setup.json').exists():raise RuntimeError('Setup already finalized')
 source=LIVE/'saves'/'oldworld';before=manifest(source)
 assert manifest(WORLD)==before, 'Incomplete or changed dev world copy'
 immutable=HERE/'perf'/'ordinary-20261103'/'baseline'/'world'
 assert manifest(immutable)==before
 for d in DIRS:
  assert manifest(ROOT/'baseline'/d)==manifest(LIVE/d)==manifest(DEV/d)
 assert (ROOT/'dev-before').is_dir()
 sys.path.insert(0,str(HERE.parent/'_struct'))
 import nbt, nbt_typed
 level=nbt_typed.load(str(WORLD/'level.dat'));old_title=level.value['Data'].value['LevelName'].value
 level.value['Data'].value['LevelName']=nbt.Str('梦想与远征 · 正式地图测试副本')
 nbt.save(level.value,str(WORLD/'level.dat'))
 assert manifest(source)==before
 runtime={d:manifest(LIVE/d) for d in DIRS}
 save_json(ROOT/'setup.json',{'created':datetime.datetime.now().isoformat(),'live':str(LIVE),'dev':str(DEV),'source_world':str(source),'dev_world':str(WORLD),'immutable_world':str(immutable),'original_title':old_title,'copy_verified':True,'files':len(before),'bytes':sum(x['bytes'] for x in before.values()),'only_dev_world_change':'level.dat Data.LevelName','source_manifest':before,'runtime_manifest':runtime})
 print('DEV_SETUP_COMPLETE',len(before),'files; formal unchanged; dev test copy ready',flush=True)
if __name__=='__main__':
 if '--finish' in sys.argv:finish_existing()
 else:main()
