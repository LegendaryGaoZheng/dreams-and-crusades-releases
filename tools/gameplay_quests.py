"""Compile the authored chapter data without renumbering existing FTB Quests."""
import collections
import hashlib
import json
from pathlib import Path
import re
import subprocess

from gameplay_data import BASE, AUDIT, OVERLAY, read, write

QUESTS = BASE / 'pack/quests'
BASELINE = '4ab2d1a'
GROUPS = {'food': '舌尖上的MC', 'mechanics': '机械与工坊', 'journey': '远征与寻宝',
          'war': '领地与征战', 'home': '家园与伙伴'}
EXISTING = {'farmer': 'food', 'industry': 'mechanics', 'quark': 'mechanics', 'guide': 'journey',
            'expedition': 'journey', 'army': 'war', 'conquest': 'war', 'contracts': 'war',
            'settlement': 'home', 'pets': 'home'}
BUDGET = dict(zip(GROUPS, (90, 65, 50, 65, 30)))
IDENTITY = re.compile(r'(?m)^\t{3}id: "([0-9A-F]{16})"')
ALL_IDS = re.compile(r'\bid:\s*"([0-9A-F]{16})"')
BLOCKS = re.compile(r'(?ms)^\t{2}\{\r?\n(.*?)^\t{2}\}')


def baseline(path):
    return subprocess.check_output(['git', 'show', f'{BASELINE}:{path.relative_to(BASE).as_posix()}'],
                                   cwd=BASE).decode('utf-8')


def sid(key):
    original = hashlib.sha256(('dream-expedition/gameplay/' + key).encode()).hexdigest()[:16].upper()
    value = int(original, 16)
    return f'{value & ((1 << 63) - 1):016X}'


def quote(text):
    return json.dumps(text, ensure_ascii=False)


def catalog():
    result = {}
    for line in (BASE / 'tools/gameplay_quests.txt').read_text(encoding='utf-8-sig').splitlines():
        if not line or line.startswith('#'):
            continue
        if line.startswith('@'):
            group, key, title, guide = line[1:].split('|')
            if group not in GROUPS or key in result or key in EXISTING:
                raise ValueError(line)
            result[key] = group, title, guide, []
        else:
            result[key][3].append(tuple(line.split('|')))
    return result


def generate():
    items = read(AUDIT / 'items.json')
    recipe_index = collections.defaultdict(list)
    for key, candidates in read(AUDIT / 'recipes.json').items():
        for _, recipe in candidates:
            stack = recipe.get('result')
            if isinstance(stack, dict) and isinstance(stack.get('id'), str):
                recipe_index[stack['id']].append((key, recipe))
    for path in (OVERLAY / 'data/dream_expedition/recipe').rglob('*.json'):
        recipe = read(path)
        stack = recipe.get('result') or (recipe.get('results') or [{}])[0]
        if 'id' in stack:
            recipe_index[stack['id']].insert(0, (path.stem, recipe))
    chapters = {}
    strings = {}
    counts = collections.Counter()
    previous = {}
    for key, group in EXISTING.items():
        path = QUESTS / 'chapters' / f'{key}.snbt'
        before = baseline(path)
        text, count = re.subn(r'(?m)^(\tgroup: ).*$', lambda m: m[1] + quote(sid('group/' + group)), before)
        if count != 1:
            raise ValueError(key)
        chapters[key] = text
        previous[key] = IDENTITY.findall(before)
        counts[group] += len(previous[key])

    for order, (key, (group, title, guide, entries)) in enumerate(catalog().items(), 30):
        chapter_id = sid('chapter/' + key)
        strings[f'chapter.{chapter_id}.title'] = title
        strings[f'chapter.{chapter_id}.chapter_subtitle'] = [guide]
        ids = [sid(f'quest/{key}/{item}') for item, _ in entries]
        if len(set(ids)) != len(ids):
            raise ValueError(f'Duplicate item in {key}')
        nodes = []
        for index, ((item, title), quest_id) in enumerate(zip(entries, ids)):
            if not re.fullmatch(r'[a-z0-9_]+:[a-z0-9_]+', item) or not (item in items or item.startswith('minecraft:')):
                raise ValueError(f'Missing item: {item}')
            # Main nodes are spaced vertically. Two optional goals branch outward.
            row, column = divmod(index, 3)
            optional = column != 0 or key in {'ruins', 'distance', 'campaign'}
            x = (0, -5, 5)[column]
            y = row * 5 + (0 if column == 0 else 2)
            # Exploration and campaign logs remain independently unlockable.
            parent = None if index == 0 or key in {'ruins', 'distance', 'campaign'} else ids[index - column if column else index - 3]
            source = recipe_index.get(item, [])
            hint = ''
            if source:
                _, recipe = source[0]
                ingredients = recipe.get('ingredients')
                if isinstance(ingredients, list):
                    names = []
                    for ingredient in ingredients:
                        if isinstance(ingredient, dict):
                            value = ingredient.get('item') or ingredient.get('tag') or ingredient.get('fluid')
                            if value:
                                names.append(items.get(value, value))
                    if names:
                        hint = '配方线索：' + '、'.join(dict.fromkeys(names)) + '。数量与替代项请查看 JEI。'
            if not hint:
                hint = '目标：在背包中准备 1 件对应物品。可通过制作、交易或探索获得。'
            strings[f'quest.{quest_id}.title'] = title
            strings[f'quest.{quest_id}.quest_desc'] = [guide, hint] + (['选做节点。'] if optional else [])
            dependency = f'\n\t\t\tdependencies: ["{parent}"]' if parent else ''
            task_id = sid(f'task/{quest_id}')
            reward_id = sid(f'reward/{quest_id}')
            nodes.append(f'''		{{
			id: "{quest_id}"{dependency}
			optional: {str(optional).lower()}
			shape: "{'circle' if optional else 'hexagon'}"
			x: {x}.0d
			y: {y}.0d
			tasks: [{{
				id: "{task_id}"
				item: {{ count: 1, id: "{item}" }}
				type: "item"
			}}]
			rewards: [{{
				id: "{reward_id}"
				type: "xp"
				xp: {5 if optional else 10}
			}}]
		}}''')
        chapters[key] = ('{\n\tdefault_hide_dependency_lines: false\n'
                         f'\tfilename: "{key}"\n\tgroup: "{sid("group/" + group)}"\n'
                         f'\tid: "{chapter_id}"\n\torder_index: {order}\n\tquest_links: []\n'
                         '\tquests: [\n' + '\n'.join(nodes) + '\n\t]\n}\n')
        counts[group] += len(entries)
    if counts != BUDGET:
        raise ValueError((counts, BUDGET))
    for group, title in GROUPS.items():
        strings[f'chapter_group.{sid("group/" + group)}.title'] = title

    graph = {}
    registry_ids = []
    overlap = []
    for key, text in chapters.items():
        registry_ids += ALL_IDS.findall(text)
        positions = set()
        for block in BLOCKS.findall(text):
            found = IDENTITY.findall(block)
            if not found:
                continue
            quest_id, = found
            deps = re.search(r'(?m)^\t{3}dependencies: \[([^]]*)\]', block)
            graph[quest_id] = re.findall(r'"([0-9A-F]{16})"', deps[1]) if deps else []
            point = tuple(re.findall(r'(?m)^\t{3}[xy]: ([-.0-9]+)d', block))
            if len(point) == 2:
                if point in positions:
                    overlap.append((key, point))
                positions.add(point)
    duplicate = [i for i, count in collections.Counter(registry_ids).items() if count > 1]
    if duplicate or len(graph) != 300:
        raise ValueError((duplicate, len(graph)))
    done = set()
    active = set()

    def visit(node):
        if node in active:
            raise ValueError(f'Quest dependency cycle: {node}')
        if node not in done:
            active.add(node)
            for parent in graph[node]:
                visit(parent)
            active.remove(node)
            done.add(node)

    for node in graph:
        visit(node)
    assert all(IDENTITY.findall(chapters[key]) == ids for key, ids in previous.items())
    if any(key not in EXISTING for key, _ in overlap):
        raise ValueError(overlap)
    for key, text in chapters.items():
        (QUESTS / 'chapters' / f'{key}.snbt').write_bytes(text.encode('utf-8'))
    groups = '\n'.join(f'\t\t{{ id: "{sid("group/" + key)}" }}' for key in GROUPS)
    (QUESTS / 'chapter_groups.snbt').write_bytes(('{\n\tchapter_groups: [\n' + groups + '\n\t]\n}\n').encode())
    language = QUESTS / 'lang/en_us.snbt'
    old = baseline(language).rstrip()
    extra = '\n'.join(f'\t{key}: {quote(value)}' for key, value in sorted(strings.items()))
    language.write_bytes((old[:old.rindex('}')].rstrip() + '\n' + extra + '\n}\n').encode())
    write(AUDIT / 'quest-validation.json',
          dict(counts=counts, existing=sum(map(len, previous.values())), total=len(graph), legacy_overlap=overlap))
    print(dict(counts), 'total', len(graph), 'legacy overlap', overlap)


if __name__ == '__main__':
    if (BASE / 'tools/quest_atlas_ids.json').exists():
        raise SystemExit('Use tools/quest_atlas.py to rebuild the current atlas and preserve its recovered IDs.')
    generate()
