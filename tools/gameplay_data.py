"""Generate the audited cookware, Create and themed loot overlays."""
import copy
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
AUDIT = BASE / '.stage/gameplay-next'
OVERLAY = BASE / 'pack/kubejs'
POT = 'farm_and_charm:cooking_pot'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def data_path(resource, directory):
    namespace, name = resource.split(':', 1)
    return OVERLAY / 'data' / namespace / directory / (name + '.json')


def recipes(inventory):
    removed = {POT, 'letsdocompat:create/crafting_bowl/dough',
               'letsdocompat:create/crafting_bowl/sweet_dough'}
    mapped = {}
    for key, candidates in inventory.items():
        for _, raw in candidates:
            if raw['type'] == 'farmersdelight:cooking':
                removed.add('letsdocompat:farm_and_charm/' + key.split(':', 1)[1])
            if raw['type'] != 'farm_and_charm:pot_cooking':
                continue
            if len(candidates) != 1 or raw.get('requiresLearning') or 'neoforge:conditions' in raw:
                raise ValueError(f'Manual cookware review required: {key}')
            name = key.rsplit('/', 1)[-1]
            removed.update({key, 'letsdocompat:farmersdelight/' + key.split(':', 1)[1]})
            if name in {'beetroot_soup', 'rabbit_stew'}:
                mapped[key] = f'farmersdelight:cooking/{name}'
                continue
            replacement = {k: copy.deepcopy(raw[k]) for k in ('ingredients', 'result', 'container') if k in raw}
            for stack in ('result', 'container'):
                if stack in replacement:
                    replacement[stack].setdefault('count', 1)
            replacement.update(type='farmersdelight:cooking', cookingtime=200,
                               experience=raw.get('experience', 0), recipe_book_tab='meals')
            new = f'dream_expedition:cooking/{name}'
            mapped[key] = new
            write(data_path(new, 'recipe'), replacement)
    for name, tag in [('dough', 'farm_and_charm:water_bottles'), ('sweet_dough', 'bakery:water_bottles')]:
        original = inventory[f'farm_and_charm:crafting_bowl/{name}'][0][1]
        ingredients = copy.deepcopy(original['ingredients'])
        matches = [i for i, x in enumerate(ingredients) if x.get('tag') == tag]
        if len(matches) != 1:
            raise ValueError(name)
        ingredients[matches[0]] = dict(type='neoforge:single', fluid='minecraft:water', amount=1000)
        write(data_path(f'dream_expedition:mixing/{name}', 'recipe'),
              dict(type='create:mixing', ingredients=ingredients, results=[original['result']]))
    for grain, amount in [('barley', 2), ('oat', 2)]:
        write(data_path(f'dream_expedition:milling/{grain}_flour', 'recipe'),
              dict(type='create:milling', ingredients=[dict(item='farm_and_charm:' + grain)],
                   results=[dict(id='farm_and_charm:flour', count=amount)], processing_time=50))
    script = OVERLAY / 'server_scripts/83_retire_letsdo_pot.js'
    script.write_text("""// Retire Farm & Charm's pot after Let’s Do Compat creates its cross-conversions.
ServerEvents.recipes(event => {
  event.remove({ type: 'farm_and_charm:pot_cooking' })
  const removed = """ + json.dumps(sorted(removed), indent=2) + """
  removed.forEach(id => event.remove({ id: id }))
})
ServerEvents.tags('item', event => event.removeAllTagsFrom('farm_and_charm:cooking_pot'))
""", encoding='utf-8')
    for folder, event in [('startup_scripts', "StartupEvents.modifyCreativeTab('farm_and_charm:farm_and_charm'"),
                          ('client_scripts', "RecipeViewerEvents.removeEntries('item'")]:
        # Use the previously verified wildcard creative-tab event registration.
        if folder == 'startup_scripts':
            pattern = (OVERLAY / folder / '80_hide_letsdo_creative.js').read_text(encoding='utf-8')
            event = next(line.split(', event')[0] for line in pattern.splitlines() if 'StartupEvents.' in line)
        (OVERLAY / folder / '83_hide_letsdo_pot.js').write_text(
            event + ", event => event.remove('farm_and_charm:cooking_pot'))\n", encoding='utf-8')
    write(data_path('farm_and_charm:blocks/cooking_pot', 'loot_table'),
          {'type': 'minecraft:block', 'pools': []})
    write(AUDIT / 'cookware-map.json', mapped)


# weight is unconditional probability in percent. One draw from each table.
LOOT = {
    'ctov:chests/village/village_farm': ('农场与温室', [
        ('farm_and_charm:barley', 2, 6, 12), ('farm_and_charm:oat', 2, 6, 10),
        ('farmersdelight:cabbage_seeds', 2, 5, 8), ('farmersdelight:tomato', 2, 5, 8),
        ('farm_and_charm:barley_seeds', 2, 5, 7)]),
    'ctov:chests/village/village_bakery': ('面包房', [
        ('farm_and_charm:flour', 1, 3, 15), ('bakery:sweet_dough', 1, 2, 10),
        ('farmersdelight:apple_pie_slice', 1, 2, 10)]),
    'ctov:chests/village/village_smith': ('铁匠铺', [
        ('create:andesite_alloy', 1, 3, 14), ('create:shaft', 1, 3, 8), ('create:cogwheel', 1, 2, 3)]),
    'kaisyn:outpost/common/food': ('前哨厨房与食物补给点', [
        ('farmersdelight:cooked_bacon', 1, 3, 13), ('farmersdelight:smoked_ham', 1, 1, 10),
        ('farmersdelight:apple_pie_slice', 1, 2, 12)]),
    'kaisyn:outpost/common/armory': ('前哨军械库与工场', [
        ('hundred_years_war:bullet', 1, 3, 21), ('hundred_years_war:handgonne', 1, 1, 4)]),
    'kaisyn:outpost/exclusives/outpost_mediterranean_barrel': ('地中海要塞储藏桶', [
        ('vinery:red_wine', 1, 2, 17), ('vinery:glowing_wine', 1, 1, 14), ('vinery:mellohi_wine', 1, 1, 4)]),
}


def loot(items, refs, tables):
    audit = {}
    for key, (label, choices) in LOOT.items():
        source, table = tables[key]
        assert refs[key] and table.get('type', 'minecraft:chest') == 'minecraft:chest', key
        assert all(item in items for item, *_ in choices), key
        base_pools = copy.deepcopy(table['pools'])
        entries = [dict(type='minecraft:empty', weight=100 - sum(x[3] for x in choices))]
        for item, minimum, maximum, weight in choices:
            entry = dict(type='minecraft:item', name=item, weight=weight)
            if (minimum, maximum) != (1, 1):
                entry['functions'] = [dict(function='minecraft:set_count',
                                           count=dict(type='minecraft:uniform', min=minimum, max=maximum))]
            entries.append(entry)
        table['pools'].append(dict(rolls=1, entries=entries))
        assert table['pools'][:-1] == base_pools
        write(data_path(key, 'loot_table'), table)
        counts = {}
        for _, structure, _ in refs[key]:
            counts[structure] = counts.get(structure, 0) + 1
        audit[key] = dict(category=label, source=source, choices=choices,
                          maximum_chests_per_template=max(counts.values()), references=counts)
    write(BASE / 'pack/gameplay-loot-audit.json', audit)


if __name__ == '__main__':
    recipes(read(AUDIT / 'recipes.json'))
    loot(*(read(AUDIT / (name + '.json')) for name in ('items', 'refs', 'tables')))
