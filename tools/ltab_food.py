"""Build the LTAB food overlay from the exact installed dev JAR.

Requires Python 3.12 and nbtlib. Run without --apply-dev to preview.
"""
import argparse
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

import nbtlib
from gameplay_data import BASE, write


SOURCE = 'create_ltab-4.1.0.jar'
SOURCE_SHA = 'd19e9de5496ba79dc8de7688adaab901af98c3b9281aae723d29ec97a2cf4d11'
# Each line is an item, minimum, maximum, and unconditional percentage.
FOOD = {
    'bakery': [('bakery:braided_bread', 1, 3, 22), ('bakery:croissant', 1, 2, 18),
               ('bakery:bread_with_jam', 1, 2, 15)],
    'mill': [('farm_and_charm:barley', 2, 5, 17), ('farm_and_charm:oat', 2, 5, 14),
             ('farm_and_charm:flour', 2, 5, 10), ('farm_and_charm:farmers_bread', 1, 1, 4)],
    'house': [('bakery:apple_jam', 1, 1, 10), ('bakery:jam_roll', 1, 2, 10),
              ('herbalbrews:lavender_tea', 1, 1, 10)],
    'cherry': [('herbalbrews:green_tea', 1, 1, 12), ('bakery:strawberry_glazed_cookie', 1, 2, 10),
               ('bakery:jam_roll', 1, 2, 8)],
    'forest': [('bakery:sweetberry_jam', 1, 1, 12), ('bakery:crusty_bread', 1, 2, 10),
               ('herbalbrews:lavender_tea', 1, 1, 8)],
    'coast': [('bakery:grilled_salmon_sandwich', 1, 2, 12), ('herbalbrews:hibiscus_tea', 1, 1, 10),
              ('bakery:jam_roll', 1, 2, 8)],
    'desert': [('bakery:crusty_bread', 1, 2, 12), ('herbalbrews:hibiscus_tea', 1, 1, 10),
               ('vinery:white_grapejuice', 1, 1, 8)],
    'rations': [('bakery:crusty_bread', 1, 3, 13), ('bakery:jam_sandwich', 1, 2, 12),
                ('brewery:gingerbread', 1, 2, 10)],
    'winter': [('farm_and_charm:barley_soup', 1, 1, 13), ('brewery:gingerbread', 1, 2, 12),
               ('herbalbrews:black_tea', 1, 1, 10)],
    'reserve': [('brewery:gingerbread', 1, 2, 12), ('bakery:crusty_bread', 1, 2, 10),
                ('vinery:red_grapejuice', 1, 1, 8)],
    'cellar': [('vinery:red_wine', 1, 1, 16), ('vinery:glowing_wine', 1, 1, 9),
               ('vinery:mellohi_wine', 1, 1, 4)],
    'dessert': [('bakery:apple_pie_slice', 1, 2, 12), ('bakery:chocolate_gateau_slice', 1, 2, 10),
                ('herbalbrews:black_tea', 1, 1, 8)],
    'salvage': [('vinery:red_wine', 1, 1, 6), ('vinery:glowing_wine', 1, 1, 3)],
}
TEMPLATES = {
    'bakery': ('plains/baker',),
    'mill': ('big_windmill', 'plains/watermill'),
    'house': ('birch/birch_house_1', 'birch/birch_house_2', 'birch/birch_house_5',
              'birch/birch_house_6', 'plains/house1', 'plains/house2', 'plains/house3',
              'plains/house4', 'plains/oldhouse', 'pillage/houses/plains_medium_house_1',
              'pillage/houses/plains_medium_house_2', 'pillage/houses/plains_small_house_2',
              'pillage/houses/plains_small_house_3', 'pillage/houses/plains_small_house_4',
              'not__junos_house'),
    'cherry': ('cherry_house',),
    'forest': ('dark_forest/dark_forest_house_1', 'dark_forest/dark_forest_house_2'),
    'coast': ('swamp/smallmangrove_house', 'swamp/smallmangrove_house3'),
    'desert': ('sand/sand_house', 'sand/sand_house_2', 'sand/sand_house_3'),
    'rations': ('railroad', 'water/oil_platform', 'birch/birch_mine'),
    'winter': ('spruce/snow_fort', 'spruce/spruce_house_1',
               'spruce/fire_tower', 'spruce/observatory'),
    'reserve': ('the_bunker', 'small_warped_house'),
    'cellar': ('not__junos_basement',),
    'dessert': ('oak_house', 'castle/kings_castle', 'castle/castle_top_room2'),
    'salvage': ('water/ocean_remnant', 'water/ocean_remnant2'),
}
CONTAINERS = {'minecraft:chest', 'minecraft:trapped_chest', 'minecraft:barrel'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def food_pool(choices):
    entries = [dict(type='minecraft:empty', weight=100 - sum(row[3] for row in choices))]
    for item, minimum, maximum, weight in choices:
        entry = dict(type='minecraft:item', name=item, weight=weight)
        if (minimum, maximum) != (1, 1):
            entry['functions'] = [dict(function='minecraft:set_count',
                                       count=dict(type='minecraft:uniform', min=minimum, max=maximum))]
        entries.append(entry)
    assert all(e['weight'] > 0 for e in entries)
    return dict(rolls=1, entries=entries)


def build(mods, output):
    source = mods / SOURCE
    assert digest(source.read_bytes()) == SOURCE_SHA, 'Review templates for this LTAB build'
    inventory = set()
    for pattern in ('letsdo-bakery-*', 'letsdo-brewery-*', 'letsdo-farm_and_charm-*',
                    'letsdo-herbalbrews-*', 'letsdo-vinery-*'):
        with ZipFile(next(mods.glob(pattern + '.jar'))) as jar:
            for name in jar.namelist():
                parts = name.split('/')
                if len(parts) == 5 and parts[0] == 'assets' and parts[2:4] == ['models', 'item']:
                    inventory.add(parts[1] + ':' + Path(parts[4]).stem)
    assert all(row[0] in inventory for choices in FOOD.values() for row in choices)
    files = {}
    audit = {}
    with ZipFile(source) as jar:
        names = set(jar.namelist())
        locations = {
            element['element'].get('location')
            for path in names if '/worldgen/template_pool/' in path and path.endswith('.json')
            for element in json.loads(jar.read(path)).get('elements', [])
        }
        assert all(f'create_ltab:{template}' in locations
                   for templates in TEMPLATES.values() for template in templates)
        for theme, templates in TEMPLATES.items():
            for template in templates:
                rel = f'data/create_ltab/structure/{template}.nbt'
                nbt = nbtlib.File.parse(io.BytesIO(gzip.decompress(jar.read(rel))))
                original = deepcopy(nbt)
                candidates = []
                for index, block in enumerate(nbt['blocks']):
                    entity = block.get('nbt', {})
                    table = str(entity.get('LootTable', ''))
                    if entity.get('id') not in CONTAINERS or not table.startswith('create_ltab:'):
                        continue
                    path = 'data/create_ltab/loot_table/' + table.split(':', 1)[1] + '.json'
                    if path in names:
                        candidates.append((index, table, path))
                assert candidates, template
                # Prefer ordinary supplies over rare and legendary containers where available.
                index, table, path = min(candidates, key=lambda row: ('basic' not in row[1], row[0]))
                new = f'dream_expedition:ltab_food/{template}'
                nbt['blocks'][index]['nbt']['LootTable'] = nbtlib.String(new)
                assert nbt['blocks'][index]['nbt'].get('Items') in (None, [])
                stream = io.BytesIO()
                nbt.write(stream)
                parsed = nbtlib.File.parse(io.BytesIO(stream.getvalue()))
                assert parsed['blocks'][index]['nbt']['LootTable'] == new
                parsed['blocks'][index]['nbt']['LootTable'] = nbtlib.String(table)
                assert parsed == original, template
                files[rel] = gzip.compress(stream.getvalue(), mtime=0)
                table_data = json.loads(jar.read(path))
                base_pools = deepcopy(table_data['pools'])
                table_data['pools'].append(food_pool(FOOD[theme]))
                assert table_data['pools'][:-1] == base_pools
                loot_rel = f'data/dream_expedition/loot_table/ltab_food/{template}.json'
                files[loot_rel] = (json.dumps(table_data, indent=2) + '\n').encode()
                audit[template] = dict(position=list(map(int, nbt['blocks'][index]['pos'])),
                                       original_table=table, new_table=new, theme=theme,
                                       choices=FOOD[theme])
    assert len(files) == 2 * len(audit)
    for name, data in files.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return files, audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dev', required=True, type=Path)
    parser.add_argument('--apply-dev', action='store_true')
    args = parser.parse_args()
    expected = Path.home() / 'Desktop/游戏/.minecraft/versions/梦想与远征_dev'
    dev = args.dev.absolute()
    if dev != expected or dev.resolve() != expected or (dev / 'mods').resolve() != dev / 'mods':
        parser.error('Expected the canonical local dev instance')
    stage = BASE / '.stage/ltab-food'
    files, audit = build(dev / 'mods', stage)
    write(stage / 'record.json', dict(source=SOURCE, source_sha256=SOURCE_SHA, templates=audit,
                                     outputs={k: digest(v) for k, v in files.items()}))
    if args.apply_dev:
        root = dev / 'kubejs'
        for name, data in files.items():
            path = root / name
            if path.resolve() != path or (path.exists() and path.read_bytes() != data):
                raise SystemExit(f'Refusing to overwrite {path}')
        for name, data in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                with path.open('xb') as handle:
                    handle.write(data)
        assert all((root / name).read_bytes() == data for name, data in files.items())
    print(len(audit), 'templates', dict(Counter(row['theme'] for row in audit.values())))


if __name__ == '__main__':
    main()
