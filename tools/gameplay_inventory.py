from pathlib import Path
import collections,gzip,json,re,sys,zipfile
sys.path[:0]=['.','_struct']
from workflow import DEV
from nbt_read import Reader
out=Path('.stage/gameplay-next');out.mkdir(parents=True,exist_ok=True)
recipes={};items={};refs=collections.defaultdict(list);tables={};other=[]
for p in (DEV/'mods').glob('*.jar'):
 with zipfile.ZipFile(p) as z:
  for n in z.namelist():
   if re.fullmatch(r'assets/[^/]+/lang/en_us.json',n):
    for key,value in json.loads(z.read(n),strict=False).items():
     if key.startswith(('item.','block.')):
      parts=key.split('.')
      if len(parts)==3: items[':'.join(parts[1:])]=value
   if re.fullmatch(r'data/[^/]+/recipe/.+\.json',n):
    ns,tail=n.split('/')[1],n.split('/recipe/')[1][:-5]
    key=f'{ns}:{tail}'; data=json.loads(z.read(n))
    recipes.setdefault(key,[]).append([p.name,data])
   if re.fullmatch(r'data/[^/]+/loot_table/.+\.json',n):
    key=n.split('/')[1]+':'+n.split('/loot_table/')[1][:-5];tables[key]=[p.name,json.loads(z.read(n))]
   if re.fullmatch(r'data/[^/]+/(structure|structures)/.+\.nbt',n):
    raw=z.read(n)
    try: obj=Reader(gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw).root()
    except (OSError,ValueError,KeyError):continue
    for b in obj.get('blocks',[]):
     tag=b.get('nbt',{})
     if 'LootTable' in tag: refs[tag['LootTable']].append([p.name,n,b.get('pos')])
for name,data in [('recipes',recipes),('items',items),('refs',refs),('tables',tables)]:
 (out/f'{name}.json').write_text(json.dumps(data,indent=1,ensure_ascii=False),encoding='utf-8')
for k,v in recipes.items():
 for p,x in v:
  if x.get('type')=='farm_and_charm:pot_cooking' or (x.get('type','').startswith('farm_and_charm:') and any(s in k for s in ('flour','oil','dough'))):
   print(k,x.get('type'),x.get('result'),x.get('container'),x.get('requiresLearning'))
print('REFERENCED TABLES',len(refs))
for k,v in refs.items():
 names=[x[1].rsplit('/',1)[-1][:-4] for x in v]
 if re.search('barn|kitchen|cellar|workshop|barrack|fort|winery|farm',k+' '+' '.join(names),re.I) and (k in tables or k.startswith('minecraft:')):
  print(k,len(v),list(dict.fromkeys(names))[:9])
