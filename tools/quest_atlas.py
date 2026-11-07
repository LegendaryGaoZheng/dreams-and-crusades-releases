"""Preserve FTB IDs recovered from dev and build a readable illustrated atlas."""
import collections
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from workflow import DEV

BASE = '1903493'
QUESTS = ROOT / 'pack/quests'
LIVE = DEV / 'config/ftbquests/quests'
STAGE = ROOT / '.stage/quest-atlas'
ID = re.compile(r'\bid:\s*"([0-9A-F]{16})"')
BLOCK = re.compile(r'(?ms)^\t{2}\{\r?\n(.*?)^\t{2}\}')
HEX = re.compile(r'(?<![A-Za-z0-9_-])([0-9A-F]{16})(?![A-Za-z0-9_-])')
GROUPS = ['FFB6EE23033F26BF','97D973C2DF3E1AE9','669605009D3D37DF',
          'E1A562F161C63102','01643A218C6A9DF4']
THEMES = ['hearth','works','frontier','banner','homestead']
CATALOG = {
    'farmer': ('food', 'field'), 'seasons': ('food', 'field'), 'cookery': ('food','line'),
    'baking': ('food','line'), 'winemaking': ('food','line'),
    'industry': ('mechanics','branch'), 'quark': ('mechanics','board'), 'power': ('mechanics','branch'),
    'processing': ('mechanics','branch'), 'harvest': ('mechanics','line'), 'transport': ('mechanics','line'),
    'guide': ('journey','line'), 'expedition': ('journey','map'), 'trail': ('journey','map'),
    'villages': ('journey','map'), 'ruins': ('journey','map'), 'distance': ('journey','map'),
    'army': ('war','orders'), 'conquest': ('war','orders'), 'contracts': ('war','orders'),
    'outpost': ('war','orders'), 'recruits': ('war','orders'), 'firearms': ('war','orders'), 'campaign': ('war','orders'),
    'settlement': ('home','board'), 'pets': ('home','board'), 'homestead': ('home','board'),
}
CRAFTS = {
    'create:water_wheel': 'create:crafting/kinetics/water_wheel',
    'create:mechanical_mixer': 'create:crafting/kinetics/mechanical_mixer',
    'create:mechanical_press': 'create:crafting/kinetics/mechanical_press',
    'create:mechanical_pump': 'create:crafting/kinetics/mechanical_pump',
    'hundred_years_war:handgonne': 'hundred_years_war:handgonne',
    'hundred_years_war:matchlock': 'hundred_years_war:matchlock',
}
PLACEMENTS = {'vinery:fermentation_barrel','create:gantry_shaft','create:track_station',
              'minecraft:bookshelf','minecraft:lectern','minecraft:beehive'}


def baseline(path):
    rel = path.relative_to(ROOT).as_posix()
    return subprocess.check_output(['git','show',f'{BASE}:{rel}'],cwd=ROOT).decode()


def stable(value):
    return f'{int(hashlib.sha256(value.encode()).hexdigest()[:16],16) & ((1 << 63)-1):016X}'


def valid(value):
    return 0 < int(value,16) < 1 << 63


def field(text,key,depth=3):
    result = re.search(rf'(?m)^\t{{{depth}}}{key}:\s*([^\r\n]+)',text)
    return result[1].strip() if result else ''


def node_key(block):
    # Positions plus referenced items/advancements distinguish generated tasks, even when IDs changed.
    refs = sorted(re.findall(r'"([a-z0-9_]+:[a-z0-9_/]+)"',block))
    types = sorted(re.findall(r'\btype:\s*"([^"]+)"',block))
    return field(block,'x'),field(block,'y'),tuple(refs),tuple(types)


def section_ids(block, name):
    match = re.search(rf'(?ms)^\t{{3}}{name}:\s*(.*?)(?=^\t{{3}}\w+:|\Z)',block)
    return ID.findall(match[1]) if match else []


def recover(chapters, groups):
    declared = set(ID.findall(groups))
    for text in chapters.values(): declared.update(ID.findall(text))
    fixed = {x for x in declared if valid(x)}
    claimed = set(fixed)
    evidence = {}
    mapping = {}

    def pair(old,new,reason):
        if valid(old) or not valid(new) or new in claimed or old in mapping:
            return
        mapping[old]=new
        claimed.add(new)
        evidence[old]=reason

    live_groups=ID.findall((LIVE/'chapter_groups.snbt').read_text(encoding='utf-8'))
    if len(live_groups)==len(GROUPS) and all(
            not valid(old) or old==new for old,new in zip(GROUPS,live_groups)):
        for old,new in zip(GROUPS,live_groups):
            pair(old,new,'saved group order matches preserved IDs')
    for filename,text in chapters.items():
        live=(LIVE/'chapters'/filename).read_text(encoding='utf-8')
        if field(text,'filename',1)!=field(live,'filename',1):continue
        authored=BLOCK.findall(text)
        runtime=BLOCK.findall(live)
        keys=collections.Counter(map(node_key,authored))
        actual=collections.defaultdict(list)
        for b in runtime:actual[node_key(b)].append(b)
        unique=[(b,actual[node_key(b)][0]) for b in authored
                if keys[node_key(b)]==1 and len(actual[node_key(b)])==1]
        if len(unique)==len(authored)==len(runtime):
            pair(ID.findall(text)[0],ID.findall(live)[0],filename+' chapter and all node signatures match')
        for before,after in unique:
            aid,bid=ID.findall(before)[0],ID.findall(after)[0]
            if valid(aid) and aid!=bid:continue
            pair(aid,bid,filename+' node signature matches')
            for role in ('tasks','rewards'):
                a,b=section_ids(before,role),section_ids(after,role)
                if len(a)==len(b) and all(not valid(x) or x==y for x,y in zip(a,b)):
                    for x,y in zip(a,b):
                        pair(x,y,filename+' matched '+role+' position')
    for old in sorted(declared-fixed-mapping.keys()):
        index=0
        while (new:=stable(f'atlas/legacy/{old}/{index}')) in claimed:index+=1
        mapping[old]=new
        claimed.add(new)
        evidence[old]='stable replacement; no proven live match'
    return mapping,evidence


def point(layout,index,depth):
    if layout=='line': return (index//3)*7,(index%3-1)*4
    if layout=='field': return (index%5)*5,(index//5)*5
    if layout=='branch': return depth*7,index*3
    if layout=='map':
        angle=index*2.399963
        radius=5+3.1*math.sqrt(index+1)
        return round(math.cos(angle)*radius,1),round(math.sin(angle)*radius,1)
    if layout=='orders': return (index//4)*7,(index%4)*5
    return (index%4)*6,(index//4)*6


def art():
    palettes=[('#27182a','#764942','#e9b277'),('#152c38','#387277','#d5c77e'),
              ('#182d39','#446f66','#d5cc91'),('#291d2d','#743a49','#e5b891'),
              ('#253428','#5b7f52','#f2d19d')]
    out=ROOT/'pack/kubejs/assets/dream_expedition/textures/quest_atlas'
    out.mkdir(parents=True,exist_ok=True)
    for i,(name,(dark,mid,light)) in enumerate(zip(THEMES,palettes)):
        image=Image.new('RGB',(144,48),dark)
        d=ImageDraw.Draw(image)
        d.rectangle((1,1,142,46),outline=light)
        d.rectangle((3,3,140,44),outline=mid)
        for x in range(8,139,8):
            y=8+((x*7+i*11)%22)
            d.point((x,y),fill=light)
        d.polygon([(4,40),(23,23),(41,36),(59,19),(82,41),(101,25),(139,40)],fill=mid)
        d.rectangle((4,40,139,43),fill=mid)
        if i==0:
            d.rectangle((57,28,86,35),fill=light)
            d.rectangle((60,36,83,40),fill='#934d46')
            for x in (64,72,80):d.line([(x,25),(x-2,19),(x+1,14)],fill=light,width=2)
        elif i==1:
            for x,y,r in [(66,26,11),(84,19,8)]:
                d.ellipse((x-r,y-r,x+r,y+r),fill=light,outline=dark,width=2)
                d.ellipse((x-3,y-3,x+3,y+3),fill=dark)
                d.line((x-r-2,y,x+r+2,y),fill=dark,width=2)
        elif i==2:
            d.polygon([(72,10),(83,26),(72,40),(61,26)],fill=light)
            d.polygon([(72,15),(76,27),(72,36),(68,27)],fill=dark)
            d.line((53,26,91,26),fill=light,width=1)
        elif i==3:
            d.line((66,12,66,41),fill=light,width=2)
            d.polygon([(67,12),(91,15),(82,21),(91,27),(67,29)],fill=light)
            d.polygon([(73,18),(81,20),(75,25)],fill=mid)
        else:
            d.rectangle((60,25,83,40),fill=light)
            d.polygon([(54,26),(72,12),(88,26)],fill='#9a543e')
            d.rectangle((69,31,74,40),fill=dark)
        image.resize((576,192),Image.Resampling.NEAREST).save(out/(name+'.png'))


def main():
    STAGE.mkdir(parents=True,exist_ok=True)
    paths=sorted((QUESTS/'chapters').glob('*.snbt'))
    chapters={p.name:baseline(p) for p in paths}
    group_source=baseline(QUESTS/'chapter_groups.snbt')
    mapfile=ROOT/'tools/quest_atlas_ids.json'
    if mapfile.exists():
        receipt=json.loads(mapfile.read_text(encoding='utf-8'))
        mapping,evidence=receipt['mapping'],receipt['evidence']
    else:
        mapping,evidence=recover(chapters,group_source)
        mapfile.write_text(json.dumps(dict(mapping=mapping,evidence=evidence),indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    translate=lambda text:HEX.sub(lambda m:mapping.get(m[1],m[1]),text)
    lang=translate(baseline(QUESTS/'lang/en_us.snbt'))
    registered=set()
    dependencies={}
    rebuilt={}
    advancements={}
    for filename,text in chapters.items():
        text=translate(text)
        key=Path(filename).stem
        group,layout=CATALOG[key]
        group_id=translate(GROUPS[list(('food','mechanics','journey','war','home')).index(group)])
        assert field(text,'group',1).strip('"')==group_id
        blocks=BLOCK.findall(text)
        group_art=THEMES[list(('food','mechanics','journey','war','home')).index(group)]
        positions=set()
        pending={}
        source_index={}
        for i,b in enumerate(blocks):
            ident=ID.findall(b)[0]
            source_index[ident]=i
            pending[ident]=re.findall(r'"([0-9A-F]{16})"',field(b,'dependencies'))
        depth_cache={}
        def depth(node,seen=frozenset()):
            if node in seen: raise ValueError(f'cycle at {node}')
            if node not in depth_cache:
                depth_cache[node]=max((depth(p,seen|{node})+1 for p in pending.get(node,[]) if p in pending),default=0)
            return depth_cache[node]
        first_item=None
        def relayout(match):
            nonlocal first_item
            b=match[1]
            ident=ID.findall(b)[0]
            index=source_index[ident]
            item_match=re.search(r'\bitem: \{ count: 1, id: "([^"]+)" \}',b)
            item=item_match[1] if item_match else None
            if not first_item and item:first_item=item
            x,y=point(layout,index,depth(ident))
            while (x,y) in positions:y+=3
            positions.add((x,y))
            b=re.sub(r'(?m)^(\t{3}x: ).*$',lambda m:f'{m[1]}{x:.1f}d',b)
            b=re.sub(r'(?m)^(\t{3}y: ).*$',lambda m:f'{m[1]}{y:.1f}d',b)
            if key in {'power','processing','harvest','transport','winemaking','firearms','homestead'} and item in (CRAFTS.keys()|PLACEMENTS) and len(section_ids(b,'tasks'))==1:
                task_id=section_ids(b,'tasks')[0]
                trigger='minecraft:recipe_crafted' if item in CRAFTS else 'minecraft:placed_block'
                conditions={'recipe_id':CRAFTS[item]} if item in CRAFTS else {'location':[{'condition':'minecraft:block_state_property','block':item}]}
                adv=f'quest_atlas/{key}/{item.split(":")[1]}'
                advancements[adv]={'criteria':{'milestone':{'trigger':trigger,'conditions':conditions}}}
                b=re.sub(r'(?ms)^\t{3}tasks: \[\{.*?^\t{3}\}\]',lambda _:
                         '\t\t\ttasks: [{\n\t\t\t\tid: "'+task_id+'"\n\t\t\t\ttype: "advancement"\n'
                         '\t\t\t\tadvancement: "dream_expedition:'+adv+'"\n\t\t\t}]',b,count=1)
            return '\t\t{\n'+b+'\t\t}'
        text=BLOCK.sub(relayout,text)
        art_id=stable('atlas/art/'+key)
        banner=(
            '\timages: [{\n'
            f'\t\tid: "{art_id}"\n\t\timage: "dream_expedition:textures/quest_atlas/{group_art}.png"\n'
            f'\t\twidth: 18.0d\n\t\theight: 6.0d\n\t\tx: 0.0d\n\t\ty: {min(y for _,y in positions)-7:.1f}d\n\t}}]\n')
        text=re.sub(r'(?ms)^\timages: \[.*?^\t\}\]\r?\n','',text,count=1)
        text=re.sub(r'(?m)^\timages: \[ *\]\r?\n','',text,count=1)
        if not field(text,'icon',1) and first_item:
            banner+='\ticon: '+json.dumps(first_item)+'\n'
        text=text.replace('\tquests: [',banner+'\tquests: [',1)
        rebuilt[filename]=text
        ids=ID.findall(text)
        if registered.intersection(ids) or len(set(ids))!=len(ids) or not all(map(valid,ids)):
            raise ValueError(filename+' invalid IDs')
        registered.update(ids)
        dependencies.update(pending)
        for ident in (ids[0],*pending):
            prefix='chapter' if ident==ids[0] else 'quest'
            if f'{prefix}.{ident}.title:' not in lang:raise ValueError(f'Unnamed {prefix} {ident}')
    if len(dependencies)!=300 or any(parent not in dependencies for deps in dependencies.values() for parent in deps):
        raise ValueError('Invalid quest graph')
    seen=set()
    def verify(node,active=frozenset()):
        if node in active:raise ValueError('Cross-chapter cycle')
        if node in seen:return
        for parent in dependencies[node]:verify(parent,active|{node})
        seen.add(node)
    for node in dependencies:verify(node)
    gunpowder=next(ID.findall(b)[0] for b in BLOCK.findall(rebuilt['firearms.snbt']) if 'minecraft:gunpowder' in b)
    lang=re.sub(rf'(?m)^\tquest\.{gunpowder}\.quest_desc:.*$',
                '\tquest.'+gunpowder+'.quest_desc: '+json.dumps([
                    '用加热的 Create 搅拌盆混合余烬面粉、木炭和红石粉。每批产出一份火药。',
                    '保留原有的怪物掉落与药水灌注路线。可在 JEI 查看加工条件。'],ensure_ascii=False),lang)
    for p in paths:p.write_bytes(rebuilt[p.name].encode())
    (QUESTS/'chapter_groups.snbt').write_bytes(translate(group_source).encode())
    for locale in ('en_us','zh_cn'):(QUESTS/'lang'/f'{locale}.snbt').write_bytes(lang.encode())
    for key,value in advancements.items():
        path=ROOT/'pack/kubejs/data/dream_expedition/advancement'/(key+'.json')
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    art()
    print('Chapters:',len(rebuilt),'quests:',len(dependencies),'advancements:',len(advancements),
          'recovered:',sum(not x.startswith('stable replacement') for x in evidence.values()),'remapped:',len(mapping))


if __name__=='__main__':
    main()
