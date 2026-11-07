"""Voxel builder + structure-template saver + isometric preview renderer."""
from __future__ import annotations

import io
import json
import os
import zipfile
from collections import OrderedDict

from PIL import Image, ImageDraw

import nbt

BASE = os.path.dirname(os.path.abspath(__file__))
REGISTRY_PATH = os.path.join(BASE, "registry.json")
COLORS_PATH = os.path.join(BASE, "block_colors.json")
VERSION_JAR = r"C:\Users\Legen\Desktop\游戏\.minecraft\versions\梦想与远征\梦想与远征.jar"
MODS_DIR = r"C:\Users\Legen\Desktop\游戏\.minecraft\versions\梦想与远征\mods"
DATA_VERSION = 3955

AIR = "minecraft:air"
VOID = "minecraft:structure_void"

# ---------------------------------------------------------------- connections
_NON_SOLID_SUFFIXES = (
    "_slab", "_stairs", "_fence", "_wall", "_pane", "_carpet", "_sign", "_torch",
    "_lantern", "_banner", "_door", "_trapdoor", "_button", "_lever", "_pressure_plate",
    "_rail", "_chain", "_vine", "_grass", "_fern", "_flower", "_sapling", "_bush",
    "_tulip", "_dandelion", "_poppy", "_lily", "_snow", "_candle", "_pot", "_web",
    "_cake", "_bed", "_scaffolding", "_ladder", "_repeater", "_comparator",
    "_tripwire", "_hook", "_frame", "_painting", "_sail", "_bearing", "_casing_hint",
)
_NON_SOLID_IDS = {
    "minecraft:air", "minecraft:structure_void", "minecraft:water", "minecraft:lava",
    "minecraft:glass_pane", "minecraft:iron_bars", "minecraft:short_grass",
    "minecraft:sweet_berry_bush", "minecraft:cobweb",
}


def _family(block_id):
    base = block_id.split(":")[-1]
    if base.endswith("_fence"):
        return "fence"
    if base.endswith("_wall"):
        return "wall"
    if base == "glass_pane" or base.endswith("_pane"):
        return "pane"
    if base == "iron_bars":
        return "bars"
    return None

# Blockstate JSONs only enumerate properties that affect the *model*, so fluid/logic states
# (`waterlogged`, `powered`, ...) are missing from the registry. Accept those by name, but
# only for names that actually exist in vanilla, so typos still get caught.
EXTRA_PROPS = {
    "waterlogged", "powered", "lit", "open", "occupied", "snowy", "hanging", "signal_fire",
    "persistent", "attached", "disarmed", "conditional", "extended", "eye", "age", "stage",
    "moisture", "level", "rotation", "axis", "facing", "half", "shape", "type", "part",
    "hinge", "distance", "note", "instrument", "north", "south", "east", "west", "up", "down",
    "power", "bites", "eggs", "hatch", "pickles", "berries", "layers", "candles", "delay",
    "locked", "in_wall", "tilt", "mode", "has_bottle_0", "has_bottle_1", "has_bottle_2",
    "has_record", "drag", "vertical_direction", "thickness", "sculk_sensor_phase",
    "bloom", "can_summon", "axis_along_first", "slot_0_occupied", "slot_1_occupied",
    "slot_2_occupied", "slot_3_occupied", "slot_4_occupied", "slot_5_occupied",
}
BOOL_PROPS = {
    "waterlogged", "powered", "lit", "open", "occupied", "snowy", "hanging", "signal_fire",
    "persistent", "attached", "disarmed", "conditional", "extended", "eye", "in_wall",
    "locked", "can_summon", "bloom",
}

# ---------------------------------------------------------------- registry
_REG = None


def registry():
    global _REG
    if _REG is None:
        with open(REGISTRY_PATH, encoding="utf-8") as fh:
            _REG = json.load(fh)
    return _REG


def validate_block(block_id, props):
    reg = registry()
    entry = reg.get(block_id)
    if entry is None:
        raise KeyError(f"unknown block id: {block_id}")
    legal = entry["props"]
    for key, value in (props or {}).items():
        if key in legal:
            if str(value) not in legal[key]:
                raise ValueError(f"{block_id}: {key}={value!r} not in {legal[key]}")
            continue
        if key not in EXTRA_PROPS:
            raise ValueError(f"{block_id}: unknown property {key!r} (legal model props: {sorted(legal)})")
        if key in BOOL_PROPS and str(value) not in ("true", "false"):
            raise ValueError(f"{block_id}: boolean property {key} got {value!r}")


# ---------------------------------------------------------------- colors
def _jar_index():
    jars = [("minecraft", VERSION_JAR)]
    for name in os.listdir(MODS_DIR):
        if name.endswith(".jar"):
            jars.append((None, os.path.join(MODS_DIR, name)))
    return jars


def build_colors():
    """Average block texture colour per block id (best effort)."""
    reg = registry()
    colors = {}
    zips = {}
    try:
        zips["minecraft"] = zipfile.ZipFile(VERSION_JAR)
        for name in os.listdir(MODS_DIR):
            if name.endswith(".jar"):
                zips[name] = zipfile.ZipFile(os.path.join(MODS_DIR, name))
        # namespace -> [zipfile]
        ns_zips = {}
        for name, zf in zips.items():
            for entry in zf.namelist():
                if entry.startswith("assets/") and "/blockstates/" in entry:
                    ns = entry.split("/")[1]
                    ns_zips.setdefault(ns, set()).add(zf)
                    break

        fallback = {
            "air": (200, 200, 210),
            "structure_void": (120, 120, 130),
        }

        for block_id, entry in reg.items():
            ns, path = block_id.split(":", 1)
            zip_candidates = ns_zips.get(ns, [])
            candidates = [
                f"assets/{ns}/textures/block/{path}.png",
                f"assets/{ns}/textures/block/{path}_top.png",
                f"assets/{ns}/textures/block/{path}_side.png",
                f"assets/{ns}/textures/block/{path}_front.png",
                f"assets/{ns}/textures/block/{path}_end.png",
                f"assets/{ns}/textures/block/{path}_still.png",
                f"assets/{ns}/textures/item/{path}.png",
            ]
            color = None
            for cand in candidates:
                for zf in zip_candidates:
                    try:
                        raw = zf.read(cand)
                    except KeyError:
                        continue
                    try:
                        img = Image.open(io.BytesIO(raw)).convert("RGBA")
                    except Exception:
                        continue
                    img = img.resize((8, 8), Image.BILINEAR)
                    pixels = [p for p in img.getdata() if p[3] > 40]
                    if not pixels:
                        continue
                    r = sum(p[0] for p in pixels) // len(pixels)
                    g = sum(p[1] for p in pixels) // len(pixels)
                    b = sum(p[2] for p in pixels) // len(pixels)
                    color = (r, g, b)
                    break
                if color:
                    break
            if color is None:
                key = path.split("/")[-1]
                color = fallback.get(key, (140, 140, 150))
            colors[block_id] = list(color)
    finally:
        for zf in zips.values():
            zf.close()
    with open(COLORS_PATH, "w", encoding="utf-8") as fh:
        json.dump(colors, fh, ensure_ascii=False, indent=0, sort_keys=True)
    return colors


_COLORS = None


def colors():
    global _COLORS
    if _COLORS is None:
        with open(COLORS_PATH, encoding="utf-8") as fh:
            _COLORS = json.load(fh)
    return _COLORS


# ---------------------------------------------------------------- builder
class Voxel:
    def __init__(self):
        self.cells = {}
        self.block_entities = {}
        self.entities = []

    def add_entity(self, x, y, z, entity_id, **nbt_fields):
        """Queue an entity to spawn with the structure (feet position, integer coords)."""
        self.entities.append({
            "pos": (int(x), int(y), int(z)),
            "id": entity_id,
            "nbt": dict(nbt_fields),
        })
        return self

    def set_nbt(self, x, y, z, mapping):
        """Attach block-entity NBT (typed nbt.* values) to the block at this position."""
        self.block_entities[(int(x), int(y), int(z))] = mapping
        return self

    # -- primitives ------------------------------------------------------
    def set(self, x, y, z, block_id, **props):
        if block_id not in (AIR, VOID):
            validate_block(block_id, props)
        self.cells[(int(x), int(y), int(z))] = (block_id, tuple(sorted(props.items())))
        return self

    def get(self, x, y, z):
        return self.cells.get((x, y, z))

    def remove(self, x, y, z):
        self.cells.pop((x, y, z), None)

    def box(self, x0, y0, z0, x1, y1, z1, block_id, **props):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    self.set(x, y, z, block_id, **props)
        return self

    def hollow_box(self, x0, y0, z0, x1, y1, z1, block_id, thickness=1, **props):
        for _ in range(thickness):
            self.walls(x0, y0, z0, x1, y1, z1, block_id, **props)
            x0, y0, z0, x1, y1, z1 = x0 + 1, y0 + 1, z0 + 1, x1 - 1, y1 - 1, z1 - 1
        return self

    def walls(self, x0, y0, z0, x1, y1, z1, block_id, **props):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                if x in (x0, x1) or z in (z0, z1):
                    for y in range(y0, y1 + 1):
                        self.set(x, y, z, block_id, **props)
        for y in (y0, y1):
            for x in range(x0, x1 + 1):
                for z in range(z0, z1 + 1):
                    self.set(x, y, z, block_id, **props)
        return self

    def fill_if_empty(self, x0, y0, z0, x1, y1, z1, block_id, **props):
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(z0, z1 + 1):
                    if (x, y, z) not in self.cells:
                        self.set(x, y, z, block_id, **props)
        return self

    def line(self, x0, y0, z0, x1, y1, z1, block_id, **props):
        dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
        steps = max(abs(dx), abs(dy), abs(dz)) or 1
        for i in range(steps + 1):
            t = i / steps
            self.set(round(x0 + dx * t), round(y0 + dy * t), round(z0 + dz * t), block_id, **props)
        return self

    def cylinder(self, cx, cz, radius, y0, y1, block_id, hollow=False, **props):
        for y in range(y0, y1 + 1):
            for x in range(int(cx - radius), int(cx + radius) + 1):
                for z in range(int(cz - radius), int(cz + radius) + 1):
                    dist = ((x - cx) ** 2 + (z - cz) ** 2) ** 0.5
                    if hollow:
                        if radius - 0.8 <= dist <= radius + 0.4:
                            self.set(x, y, z, block_id, **props)
                    elif dist <= radius + 0.3:
                        self.set(x, y, z, block_id, **props)
        return self

    # -- composite helpers ----------------------------------------------
    def powered_wheel(self, cx, cy, cz, facing="south", radius=3, sail="create:white_sail",
                      housing="create:andesite_casing"):
        """Mechanical bearing driven by a hidden creative motor, plus a sail cross.

        Verified in-game: a mechanical bearing fed by a creative motor assembles its
        contraption by itself when the chunk loads (windmill bearings do not, because
        structure placement never fires the neighbour update that queues assembly).
        """
        dx, dy, dz = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0),
                      "west": (-1, 0, 0), "up": (0, 1, 0), "down": (0, -1, 0)}[facing]
        self.set(cx, cy, cz, "create:mechanical_bearing", facing=facing)
        mx, my, mz = cx - dx, cy - dy, cz - dz
        self.set(mx, my, mz, "create:creative_motor", facing=facing)
        # hide the motor inside a casing box (bearing side stays open)
        if facing in ("south", "north"):
            for (ox, oy) in ((-1, 0), (1, 0), (0, 1), (0, -1)):
                self.set(mx + ox, my + oy, mz, housing)
            self.set(mx, my, mz - dz, housing)
        elif facing in ("east", "west"):
            for (oz, oy) in ((-1, 0), (1, 0), (0, 1), (0, -1)):
                self.set(mx, my + oy, mz + oz, housing)
            self.set(mx - dx, my, mz, housing)
        else:
            for (ox, oz) in ((-1, 0), (1, 0), (0, 1), (0, -1)):
                self.set(mx + ox, my, mz + oz, housing)
            self.set(mx, my - dy, mz, housing)

        # sail plane one block in front of the bearing
        px, py, pz = cx + dx, cy + dy, cz + dz

        def at(u, v):
            if facing in ("south", "north"):
                return (px + u, py + v, pz)
            if facing in ("east", "west"):
                return (px, py + v, pz + u)
            return (px + u, py, pz + v)

        for k in range(1, radius + 1):
            for u, v in ((k, 0), (-k, 0), (0, k), (0, -k)):
                x, y, z = at(u, v)
                self.set(x, y, z, sail, facing=facing)
        for u, v in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            x, y, z = at(u, v)
            self.set(x, y, z, "create:sail_frame", facing=facing)
        return self

    def windmill_wheel(self, cx, cy, cz, facing="south", radius=3, sail="create:white_sail"):
        """Windmill bearing + a sail cross in the plane right in front of it.

        Layout taken from create_ltab's `big_windmill.nbt`: the bearing sits one block
        behind the sail plane and faces it, and every sail shares the same facing value.
        """
        dx, dy, dz = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0),
                      "west": (-1, 0, 0), "up": (0, 1, 0), "down": (0, -1, 0)}[facing]
        self.set(cx, cy, cz, "create:windmill_bearing", facing=facing)
        # Create only assembles a bearing when the block is actually placed by a player;
        # a structure template can never start it, so keep the wheel purely decorative.
        px, py, pz = cx + dx, cy + dy, cz + dz

        def at(u, v):
            if facing in ("south", "north"):
                return (px + u, py + v, pz)
            if facing in ("east", "west"):
                return (px, py + v, pz + u)
            return (px + u, py, pz + v)

        for k in range(1, radius + 1):
            for u, v in ((k, 0), (-k, 0), (0, k), (0, -k)):
                x, y, z = at(u, v)
                self.set(x, y, z, sail, facing=facing)
        for u, v in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            x, y, z = at(u, v)
            self.set(x, y, z, "create:sail_frame", facing=facing)
        return self

    # -- connection baking ------------------------------------------------
    def is_solid(self, x, y, z):
        cell = self.cells.get((x, y, z))
        if not cell:
            return False
        block_id = cell[0]
        if block_id in _NON_SOLID_IDS:
            return False
        if _family(block_id):
            return False
        base = block_id.split(":")[-1]
        for suffix in _NON_SOLID_SUFFIXES:
            if base.endswith(suffix):
                return False
        return True

    def autoconnect(self):
        """Bake fence / wall / pane / bars connection states from voxel neighbours.

        World generation does not reliably trigger block-neighbour updates, so templates
        must store the connected states themselves or fences render as isolated posts.
        """
        dirs = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0), "west": (-1, 0, 0)}
        for (x, y, z), (block_id, props) in list(self.cells.items()):
            fam = _family(block_id)
            if not fam:
                continue
            legal = registry()[block_id]["props"]
            new_props = dict(props)
            for direction, (dx, dy, dz) in dirs.items():
                if direction not in legal and direction not in ("north", "south", "east", "west"):
                    continue
                neighbour = self.cells.get((x + dx, y + dy, z + dz))
                same_family = bool(neighbour) and _family(neighbour[0]) == fam
                solid = self.is_solid(x + dx, y + dy, z + dz)
                if fam in ("fence", "pane", "bars"):
                    if solid or same_family:
                        new_props[direction] = "true"
                    elif fam in ("pane", "bars"):
                        new_props[direction] = "false"
                else:  # wall
                    if solid:
                        new_props[direction] = "tall"
                    elif same_family:
                        new_props[direction] = "low"
                    else:
                        new_props.pop(direction, None)
            self.cells[(x, y, z)] = (block_id, tuple(sorted(new_props.items())))
        return self

    # -- output ----------------------------------------------------------
    def bounds(self):
        xs = [k[0] for k in self.cells]
        ys = [k[1] for k in self.cells]
        zs = [k[2] for k in self.cells]
        return min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)

    def save(self, path, origin="min", loot_table=None):
        """Write a gzipped structure template. Coordinates are shifted so min = 0."""
        self.autoconnect()
        x0, y0, z0, x1, y1, z1 = self.bounds()
        sx, sy, sz = x1 - x0 + 1, y1 - y0 + 1, z1 - z0 + 1
        palette = []
        palette_index = {}
        blocks = []
        for (x, y, z), (block_id, props) in sorted(self.cells.items()):
            key = (block_id, props)
            if key not in palette_index:
                entry = {"Name": nbt.Str(block_id)}
                if props:
                    entry["Properties"] = nbt.Compound({k: nbt.Str(v) for k, v in props})
                palette_index[key] = len(palette)
                palette.append(nbt.Compound(entry))
            block_tag = {
                "pos": nbt.ListTag(nbt.TAG_INT, [nbt.Int(x - x0), nbt.Int(y - y0), nbt.Int(z - z0)]),
                "state": nbt.Int(palette_index[key]),
            }
            if loot_table and block_id in ("minecraft:chest", "minecraft:barrel", "minecraft:trapped_chest"):
                block_tag["nbt"] = nbt.Compound({"LootTable": nbt.Str(loot_table)})
            extra = self.block_entities.get((x, y, z))
            if extra:
                block_tag["nbt"] = nbt.Compound(dict(extra))
            blocks.append(nbt.Compound(block_tag))
        # entity list (recruits soldiers, animals, ...)
        entity_tags = []
        for ent in self.entities:
            ex, ey, ez = ent["pos"]
            rx, ry, rz = ex - x0 + 0.5, ey - y0, ez - z0 + 0.5
            payload = dict(ent.get("nbt", {}))
            payload["id"] = nbt.Str(ent["id"])
            payload["Pos"] = nbt.ListTag(nbt.TAG_DOUBLE, [nbt.Double(rx), nbt.Double(ry), nbt.Double(rz)])
            payload.setdefault("PersistenceRequired", nbt.Byte(1))
            entity_tags.append(nbt.Compound({
                "pos": nbt.ListTag(nbt.TAG_DOUBLE, [nbt.Double(rx), nbt.Double(ry), nbt.Double(rz)]),
                "blockPos": nbt.ListTag(nbt.TAG_INT, [nbt.Int(int(ex) - x0), nbt.Int(int(ey) - y0), nbt.Int(int(ez) - z0)]),
                "nbt": nbt.Compound(payload),
            }))
        root = {
            "size": nbt.ListTag(nbt.TAG_INT, [nbt.Int(sx), nbt.Int(sy), nbt.Int(sz)]),
            "palette": nbt.ListTag(nbt.TAG_COMPOUND, palette),
            "blocks": nbt.ListTag(nbt.TAG_COMPOUND, blocks),
            "entities": nbt.ListTag(nbt.TAG_COMPOUND, entity_tags),
            "DataVersion": nbt.Int(DATA_VERSION),
        }
        os.makedirs(os.path.dirname(path), exist_ok=True)
        nbt.save(root, path)
        return (sx, sy, sz)

    # -- preview ---------------------------------------------------------
    def _render_cells(self, cells, path, scale):
        cols = colors()
        xs = [k[0] for k in cells]
        ys = [k[1] for k in cells]
        zs = [k[2] for k in cells]
        x0, x1, y0, y1, z0, z1 = min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)
        w = (x1 - x0 + z1 - z0 + 3) * scale
        h = int((x1 - x0 + z1 - z0 + 3) * scale * 0.5) + (y1 - y0 + 2) * scale
        img = Image.new("RGBA", (int(w), int(h)), (26, 30, 42, 255))
        draw = ImageDraw.Draw(img)

        def iso(x, y, z):
            sx = (x - x0 - (z - z0)) * scale + (z1 - z0 + 1) * scale
            sy = (x - x0 + z - z0) * scale * 0.5 - (y - y0) * scale + (y1 - y0 + 2) * scale
            return sx, sy

        ordered = sorted(cells.items(), key=lambda kv: (kv[0][0] + kv[0][2], kv[0][1]))
        for (x, y, z), (block_id, props) in ordered:
            if block_id == AIR:
                continue
            base = cols.get(block_id, [140, 140, 150])
            if block_id == VOID:
                base = [80, 80, 110]
            top = tuple(min(255, int(c * 1.05)) for c in base)
            left = tuple(int(c * 0.72) for c in base)
            right = tuple(int(c * 0.52) for c in base)
            px, py = iso(x, y, z)
            draw.polygon([(px, py), (px + scale, py + scale / 2), (px, py + scale), (px - scale, py + scale / 2)], fill=top, outline=tuple(int(c * 0.88) for c in top))
            draw.polygon([(px - scale, py + scale / 2), (px, py + scale), (px, py + 2 * scale), (px - scale, py + 1.5 * scale)], fill=left, outline=tuple(int(c * 0.8) for c in left))
            draw.polygon([(px, py + scale), (px + scale, py + scale / 2), (px + scale, py + 1.5 * scale), (px, py + 2 * scale)], fill=right, outline=tuple(int(c * 0.8) for c in right))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        img.save(path, "PNG")
        return img

    def render(self, path, scale=6):
        return self._render_cells(self.cells, path, scale)

    def render_sheet(self, path, scale=6):
        """Four isometric views (0/90/180/270) in one 2x2 sheet — easier to judge a design."""
        x0, y0, z0, x1, y1, z1 = self.bounds()
        views = []
        for rot in range(4):
            cells = {}
            for (x, y, z), cell in self.cells.items():
                if rot == 0:
                    px, pz = x, z
                elif rot == 1:
                    px, pz = z1 - z, x
                elif rot == 2:
                    px, pz = x1 - x, z1 - z
                else:
                    px, pz = z, x1 - x
                cells[(px, y, pz)] = cell
            tmp = os.path.join(os.path.dirname(path), f".rot{rot}.png")
            views.append(self._render_cells(cells, tmp, scale))
        w = max(v.width for v in views)
        h = max(v.height for v in views)
        sheet = Image.new("RGBA", (w * 2, h * 2), (18, 20, 30, 255))
        for i, v in enumerate(views):
            sheet.paste(v, ((i % 2) * w, (i // 2) * h))
        sheet.save(path, "PNG")
        for rot in range(4):
            tmp = os.path.join(os.path.dirname(path), f".rot{rot}.png")
            if os.path.exists(tmp):
                os.remove(tmp)
        return sheet.size


if __name__ == "__main__":
    build_colors()
    print("colors:", len(colors()), "->", COLORS_PATH)
