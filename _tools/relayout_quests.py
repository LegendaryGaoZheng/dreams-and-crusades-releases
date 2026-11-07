# -*- coding: utf-8 -*-
"""Rebuild quest graph (single root per chapter), lay out nodes naturally, place banners clear of nodes."""
import os, re, hashlib

from pathlib import Path
import argparse
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workflow import legacy_quest_chapters

parser = argparse.ArgumentParser(description="Historical quest draft tool. Use a fresh staged copy.")
parser.add_argument("--chapters", required=True)
BASE = legacy_quest_chapters(parser.parse_args().chapters)
BANNERS = {
    "guide": "banner_guide.png", "settlement": "banner_settlement.png",
    "industry": "banner_industry.png", "army": "banner_army.png",
    "expedition": "banner_expedition.png", "conquest": "banner_conquest.png",
    "contracts": "banner_contracts.png", "farmer": "banner_farmer.png",
    "pets": "banner_pets.png", "quark": "banner_quark.png",
}

def h(s):
    return int(hashlib.md5(s.encode()).hexdigest()[:8], 16)

def find_quests_span(t):
    i = t.find("quests: [")
    if i < 0:
        return None
    start = t.find("[", i)
    depth = 0
    for j in range(start, len(t)):
        if t[j] == "[":
            depth += 1
        elif t[j] == "]":
            depth -= 1
            if depth == 0:
                return start, j
    return None

def split_blocks(t):
    span = find_quests_span(t)
    if not span:
        return [], None
    a, b = span
    blocks = []
    depth = 0
    start = None
    for j in range(a + 1, b):
        ch = t[j]
        if ch == "{":
            if depth == 0:
                start = j
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                blocks.append((start, j + 1))
                start = None
    return blocks, span

def block_field(block, name):
    m = re.search(r"\b%s: (\"[^\"]*\"|[\d.\-]+d?)" % name, block)
    return m.group(1) if m else None

def get_deps(block):
    m = re.search(r"dependencies: \[([^\]]*)\]", block)
    if not m:
        return []
    return re.findall(r'"([0-9A-F]{16})"', m.group(1))

def set_field(block, name, value):
    pat = re.compile(r"(\n\t\t\t%s: )([^\n]*)" % name)
    if pat.search(block):
        return pat.sub(lambda m: m.group(1) + value, block, count=1)
    return block

def layout_chapter(fname, t):
    blocks, span = split_blocks(t)
    nodes = {}
    order = []
    for (a, b) in blocks:
        raw = t[a:b]
        q = re.search(r'id: "([0-9A-F]{16})"', raw)
        if not q:
            continue
        qid = q.group(1)
        size_s = block_field(raw, "size")
        size = float(size_s[:-1]) if size_s and size_s.endswith("d") else 1.0
        y_s = block_field(raw, "y")
        y = float(y_s[:-1]) if y_s and y_s.endswith("d") else 0.0
        nodes[qid] = {"id": qid, "size": size, "y0": y, "deps": get_deps(raw), "raw": raw, "span": (a, b)}
        order.append(qid)

    # choose root: node with no deps (or first), attach other roots to it
    roots = [n for n in order if not nodes[n]["deps"]]
    if not roots:
        roots = [order[0]]
    main = roots[0]
    for r in roots[1:]:
        nodes[r]["deps"] = [main]

    # children
    children = {n: [] for n in order}
    for n in order:
        for d in nodes[n]["deps"]:
            if d in children:
                children[d].append(n)
    # order children by original y (keep intent)
    for k in children:
        children[k].sort(key=lambda c: (nodes[c]["y0"], c))

    # depth
    depth = {n: 0 for n in order}
    seen = set()
    def dfs(n, d, stack):
        if n in stack:
            return
        depth[n] = max(depth[n], d)
        for c in children[n]:
            dfs(c, d + 1, stack | {n})
    dfs(main, 0, set())
    # nodes unreachable -> attach to main
    reach = set()
    def mark(n):
        if n in reach:
            return
        reach.add(n)
        for c in children[n]:
            mark(c)
    mark(main)
    for n in order:
        if n not in reach:
            nodes[n]["deps"] = [main]
            children[main].append(n)
            depth[n] = 1

    # y layout: leaves stacked
    slot = [0]
    ys = {}
    def assign(n):
        kids = children[n]
        if not kids:
            ys[n] = -slot[0] * 4.0
            slot[0] += 1
            return ys[n]
        vals = [assign(c) for c in kids]
        ys[n] = sum(vals) / len(vals)
        return ys[n]
    assign(main)
    # ensure every node has y
    for n in order:
        if n not in ys:
            ys[n] = -slot[0] * 4.0
            slot[0] += 1

    # final coords with deterministic jitter
    coords = {}
    for n in order:
        x = depth.get(n, 0) * 5.0 + ((h(n) % 7) - 3) * 0.12
        y = ys[n] + ((h(n + "y") % 5) - 2) * 0.18
        coords[n] = [x, y]

    # collision resolution
    ids = list(order)
    for _ in range(60):
        moved = False
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                (x1, y1), (x2, y2) = coords[a], coords[b]
                r1 = nodes[a]["size"] / 2 + 0.6
                r2 = nodes[b]["size"] / 2 + 0.6
                if abs(x1 - x2) < (r1 + r2) and abs(y1 - y2) < (r1 + r2):
                    # push the one with larger y downward (more negative)
                    if y1 <= y2:
                        coords[a][1] -= 3.2
                    else:
                        coords[b][1] -= 3.2
                    moved = True
        if not moved:
            break

    # banner: above the topmost node (min y), clear by 6 units
    min_y = min(v[1] for v in coords.values())
    min_x = min(v[0] for v in coords.values())
    banner_x = min_x
    banner_y = min_y - 6.0

    # rewrite blocks from bottom to top to keep offsets
    for n in sorted(order, key=lambda q: nodes[q]["span"][0], reverse=True):
        a, b = nodes[n]["span"]
        raw = t[a:b]
        deps = nodes[n]["deps"]
        # deps line
        if deps:
            dep_line = '\t\t\tdependencies: [' + ", ".join('"%s"' % d for d in deps) + ']'
            if re.search(r"\n\t\t\tdependencies: \[[^\]]*\]", raw):
                raw = re.sub(r"\n\t\t\tdependencies: \[[^\]]*\]", "\n" + dep_line, raw, count=1)
            else:
                raw = raw[:raw.find("\n")] + "\n" + dep_line + raw[raw.find("\n"):]
        else:
            raw = re.sub(r"\n\t\t\tdependencies: \[[^\]]*\]", "", raw, count=1)
        raw = set_field(raw, "x", "%.1fd" % coords[n][0])
        raw = set_field(raw, "y", "%.1fd" % coords[n][1])
        t = t[:a] + raw + t[b:]

    # images: replace existing images block
    if fname in BANNERS:
        new_img = ("\timages: [{\n\t\theight: 4.0d\n\t\timage: \"dream_expedition:textures/quest_art/banners/%s\"\n"
                   "\t\trotation: 0.0d\n\t\twidth: 16.0d\n\t\tx: %.1fd\n\t\ty: %.1fd\n\t}]") % (
            BANNERS[fname], banner_x, banner_y)
        if "images: [" in t:
            # bracket-match images array
            k = t.find("images: [")
            start = t.find("[", k)
            depth = 0
            for j in range(start, len(t)):
                if t[j] == "[":
                    depth += 1
                elif t[j] == "]":
                    depth -= 1
                    if depth == 0:
                        t = t[:k] + new_img + t[j + 1:]
                        break
        else:
            t = t.replace("\ticon:", new_img + "\n\ticon:", 1)
    return t, coords, banner_x, banner_y

for f in sorted(os.listdir(BASE)):
    if not f.endswith(".snbt"):
        continue
    fname = f[:-5]
    p = os.path.join(BASE, f)
    t = open(p, encoding="utf-8").read()
    t2, coords, bx, by = layout_chapter(fname, t)
    open(p, "w", encoding="utf-8").write(t2)
    print(fname, "nodes", len(coords), "banner", round(bx, 1), round(by, 1))
