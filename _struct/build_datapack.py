"""Package the six landmarks into a 1.21.1 datapack (worldgen jigsaw structures + loot)."""
from __future__ import annotations

import json
import os
import shutil
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
NBT_DIR = os.path.join(BASE, "out", "nbt")
BUILD_DIR = os.path.join(BASE, "out", "datapack")
ZIP_PATH = os.path.join(BASE, "out", "dream_expedition_datapack.zip")
NS = "dream_expedition"
PACK_FORMAT = 48

# name -> structure settings
STRUCTURES = {
    "camping_tent": {
        "biomes": ["#minecraft:is_forest", "#minecraft:is_taiga", "minecraft:plains", "minecraft:sunflower_plains"],
        "adaptation": "beard_thin",
        "spacing": 34, "separation": 12, "salt": 4171201,
        "mossiness": 0.05, "integrity": 1.0,
        "loot": "common",
    },
    "mine_entrance": {
        "biomes": ["#minecraft:is_mountain", "#minecraft:is_hill"],
        "adaptation": "beard_box",
        "spacing": 40, "separation": 16, "salt": 4171202,
        "mossiness": 0.35, "integrity": 1.0,
        "loot": "rare",
    },
    "abandoned_outpost": {
        "biomes": ["minecraft:plains", "minecraft:sunflower_plains", "#minecraft:is_forest", "#minecraft:is_beach"],
        "adaptation": "beard_box",
        "spacing": 44, "separation": 18, "salt": 4171204,
        "mossiness": 0.55, "integrity": 0.95,
        "loot": "common",
    },
    "signal_tower": {
        "biomes": ["#minecraft:is_beach", "minecraft:plains", "minecraft:sunflower_plains", "#minecraft:is_hill"],
        "adaptation": "none",
        "spacing": 64, "separation": 28, "salt": 4171205,
        "mossiness": 0.3, "integrity": 0.97,
        "loot": "epic",
    },
    "old_dock": {
        "biomes": ["#minecraft:is_beach", "#minecraft:is_river"],
        "adaptation": "none",
        "spacing": 36, "separation": 14, "salt": 4171206,
        "mossiness": 0.45, "integrity": 0.95,
        "loot": "common",
    },
    "abandoned_helipad": {
        "biomes": ["minecraft:plains", "minecraft:sunflower_plains", "#minecraft:is_beach", "#minecraft:is_savanna"],
        "adaptation": "beard_thin",
        "spacing": 48, "separation": 20, "salt": 4171207,
        "mossiness": 0.35, "integrity": 0.93,
        "loot": "rare",
    },
    "chicken_statue": {
        "biomes": ["minecraft:plains", "minecraft:sunflower_plains", "#minecraft:is_forest"],
        "adaptation": "beard_thin",
        "spacing": 40, "separation": 16, "salt": 4171208,
        "mossiness": 0.2, "integrity": 0.99,
        "loot": "epic",
    },
}

LOOT_COMMON = {
    "rolls": {"min": 2, "max": 4},
    "entries": [
        ("minecraft:bread", 10, (1, 3)),
        ("minecraft:torch", 8, (2, 6)),
        ("minecraft:oak_planks", 8, (4, 10)),
        ("minecraft:coal", 7, (2, 6)),
        ("minecraft:string", 6, (1, 4)),
        ("minecraft:leather", 5, (1, 3)),
        ("minecraft:iron_nugget", 6, (3, 8)),
        ("create:andesite_alloy", 4, (2, 5)),
    ],
}

LOOT_RARE = {
    "rolls": {"min": 2, "max": 4},
    "entries": [
        ("minecraft:iron_ingot", 10, (1, 4)),
        ("minecraft:gold_nugget", 8, (4, 10)),
        ("minecraft:redstone", 7, (2, 6)),
        ("minecraft:gunpowder", 6, (2, 5)),
        ("minecraft:copper_ingot", 6, (2, 5)),
        ("create:brass_ingot", 5, (1, 3)),
        ("create:cogwheel", 4, (1, 2)),
        ("minecraft:iron_pickaxe", 2, (1, 1)),
    ],
}

LOOT_EPIC = {
    "rolls": {"min": 3, "max": 5},
    "entries": [
        ("minecraft:diamond", 2, (1, 2)),
        ("minecraft:emerald", 3, (1, 3)),
        ("minecraft:gold_ingot", 6, (1, 4)),
        ("minecraft:ender_pearl", 4, (1, 2)),
        ("create:precision_mechanism", 2, (1, 1)),
        ("create:brass_casing", 4, (1, 3)),
        ("minecraft:iron_block", 3, (1, 2)),
    ],
}

LOOT_TIERS = {"common": LOOT_COMMON, "rare": LOOT_RARE, "epic": LOOT_EPIC}


def _write(path, data, raw=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        if raw:
            fh.write(data)
        else:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")


def loot_table(tier):
    spec = LOOT_TIERS[tier]
    entries = []
    for name, weight, (lo, hi) in spec["entries"]:
        entries.append(
            {
                "type": "minecraft:item",
                "name": name,
                "weight": weight,
                "functions": [{"function": "minecraft:set_count", "count": {"min": lo, "max": hi}}],
            }
        )
    return {"type": "minecraft:chest", "pools": [{"rolls": spec["rolls"], "entries": entries}]}


def build():
    if os.path.isdir(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    data_root = os.path.join(BUILD_DIR, "data", NS)
    os.makedirs(data_root, exist_ok=True)

    _write(
        os.path.join(BUILD_DIR, "pack.mcmeta"),
        {"pack": {"pack_format": PACK_FORMAT, "description": "梦想与远征 · 远征地标 (r3)"}},
    )

    for name, cfg in STRUCTURES.items():
        src_nbt = os.path.join(NBT_DIR, name + ".nbt")
        if not os.path.exists(src_nbt):
            raise FileNotFoundError(src_nbt)
        dst_nbt = os.path.join(data_root, "structure", name + ".nbt")
        os.makedirs(os.path.dirname(dst_nbt), exist_ok=True)
        shutil.copy2(src_nbt, dst_nbt)

        _write(
            os.path.join(data_root, "tags", "worldgen", "biome", "has_structure", name + ".json"),
            {"values": cfg["biomes"]},
        )
        _write(
            os.path.join(data_root, "worldgen", "structure", name + ".json"),
            {
                "type": "minecraft:jigsaw",
                "biomes": f"#{NS}:has_structure/{name}",
                "step": "surface_structures",
                "spawn_overrides": {},
                "terrain_adaptation": cfg["adaptation"],
                "start_pool": f"{NS}:{name}/start_pool",
                "size": 1,
                "project_start_to_heightmap": "WORLD_SURFACE_WG",
                "start_height": {"absolute": 0},
                "max_distance_from_center": 80,
                "use_expansion_hack": False,
            },
        )
        _write(
            os.path.join(data_root, "worldgen", "template_pool", name, "start_pool.json"),
            {
                "fallback": "minecraft:empty",
                "elements": [
                    {
                        "weight": 1,
                        "element": {
                            "element_type": "minecraft:single_pool_element",
                            "location": f"{NS}:{name}",
                            "processors": f"{NS}:{name}_decay",
                            "projection": "rigid",
                        },
                    }
                ],
            },
        )
        _write(
            os.path.join(data_root, "worldgen", "structure_set", name + ".json"),
            {
                "placement": {
                    "type": "minecraft:random_spread",
                    "spacing": cfg["spacing"],
                    "separation": cfg["separation"],
                    "salt": cfg["salt"],
                },
                "structures": [{"structure": f"{NS}:{name}", "weight": 1}],
            },
        )
        _write(
            os.path.join(data_root, "worldgen", "processor_list", name + "_decay.json"),
            {
                "processors": [
                    {"processor_type": "minecraft:block_rot", "integrity": cfg["integrity"]},
                    {
                        "processor_type": "minecraft:rule",
                        "rules": [
                            {
                                "input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:stone_bricks", "probability": cfg["mossiness"]},
                                "location_predicate": {"predicate_type": "minecraft:always_true"},
                                "output_state": {"Name": "minecraft:mossy_stone_bricks"},
                            },
                            {
                                "input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:spruce_planks", "probability": cfg["mossiness"] * 0.4},
                                "location_predicate": {"predicate_type": "minecraft:always_true"},
                                "output_state": {"Name": "minecraft:spruce_planks"},
                            },
                        ],
                    },
                ]
            },
        )
        _write(
            os.path.join(data_root, "loot_table", "chests", name + ".json"),
            loot_table(cfg["loot"]),
        )

    _write(
        os.path.join(data_root, "worldgen", "structure_set", "landmarks_all.json"),
        {
            "placement": {"type": "minecraft:concentric_rings", "distance": 0, "spread": 0, "count": 0, "preferred_biomes": "#minecraft:is_overworld", "salt": 1},
            "structures": [],
        },
    ) if False else None

    # ---- /function dream_expedition:place/<name> helpers ------------------
    # `/place structure` is unreliable in this pack, so ship structure-block helpers.
    import nbt_read as _nbt_read

    sb_template = (
        'minecraft:structure_block{mode:"LOAD",name:"dream_expedition:@NAME@",'
        'posX:1,posY:0,posZ:0,sizeX:@SX@,sizeY:@SY@,sizeZ:@SZ@,'
        'integrity:1.0f,seed:0L,powered:0b,showBoundingBox:0b,'
        'rotation:"NONE",mirror:"NONE",metadata:""}'
    )
    place_dir = os.path.join(data_root, "function", "place")
    os.makedirs(place_dir, exist_ok=True)
    for name in STRUCTURES:
        template_path = os.path.join(NBT_DIR, name + ".nbt")
        if not os.path.exists(template_path):
            continue
        size = _nbt_read.load(template_path)["size"]
        sb = (sb_template
              .replace("@NAME@", name)
              .replace("@SX@", str(size[0]))
              .replace("@SY@", str(size[1]))
              .replace("@SZ@", str(size[2])))
        body = (
            f"say [梦想与远征] 正在生成 {name}\n"
            f"execute at @s run setblock ~ ~ ~ {sb}\n"
            "execute at @s run setblock ~ ~ ~2 minecraft:redstone_block\n"
            "execute at @s run schedule function dream_expedition:place/cleanup 5t\n"
        )
        _write(os.path.join(place_dir, name + ".mcfunction"), body, raw=True)
    _write(
        os.path.join(place_dir, "cleanup.mcfunction"),
        "setblock ~ ~ ~ minecraft:air\nsetblock ~ ~ ~2 minecraft:air\nsay [梦想与远征] 生成完成\n",
        raw=True,
    )

    readme = """# 梦想与远征 · 远征地标

六个地标的 worldgen 数据包（1.21.1，pack_format 48）。

| 地标 | 群系 | 地形贴合 | 间距/间隔 | 战利品 |
|---|---|---|---|---|
| 露营帐篷 | 森林/针叶林/平原 | beard_thin | 34/12 | 普通 |
| 矿洞入口 | 山地/丘陵 | beard_box | 40/16 | 稀有 |
| 失事飞艇 | 山地/平原/热带草原 | beard_thin | 56/24 | 稀有 |
| 废弃前哨 | 平原/森林/沙滩 | beard_box | 44/18 | 普通 |
| 信号塔 | 沙滩/平原/丘陵 | none | 64/28 | 史诗 |
| 旧码头 | 沙滩/河流 | none | 36/14 | 普通 |

全部结构 `size = 1`（单体，不拼接），`start_height = WORLD_SURFACE_WG`。

放置方式：把本数据包放进 `config/paxi/datapacks/`（Paxi 全局数据包），或某个存档的 `datapacks/`。
"""
    with open(os.path.join(BUILD_DIR, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(readme)

    # zip with forward slashes
    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(BUILD_DIR):
            for fn in files:
                full = os.path.join(root, fn)
                arc = os.path.relpath(full, BUILD_DIR).replace(os.sep, "/")
                zf.write(full, arc)
    return ZIP_PATH


if __name__ == "__main__":
    path = build()
    print("datapack:", path, os.path.getsize(path), "bytes")
    with zipfile.ZipFile(path) as zf:
        for name in sorted(zf.namelist()):
            print("  ", name, zf.getinfo(name).file_size)
