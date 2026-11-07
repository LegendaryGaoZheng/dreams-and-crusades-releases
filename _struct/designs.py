"""Landmark structure designs — batch 1: camping tent + mine entrance."""
from __future__ import annotations

import os

from voxel import Voxel, AIR, VOID

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
NBT_DIR = os.path.join(OUT_DIR, "nbt")
IMG_DIR = os.path.join(OUT_DIR, "preview")


def _save(vox: Voxel, name: str, scale: int = 6):
    nbt_path = os.path.join(NBT_DIR, name + ".nbt")
    size = vox.save(nbt_path, loot_table=f"dream_expedition:chests/{name}")
    img_path = os.path.join(IMG_DIR, name + ".png")
    vox.render_sheet(img_path, scale=scale)
    return size, nbt_path, img_path


# ------------------------------------------------------------------ 1. 露营帐篷
def camping_tent() -> Voxel:
    v = Voxel()
    RIDGE_X = 6
    Z0, Z1 = 2, 8

    # ---- 地面：铺满一层，保证上方方块都有支撑
    for x in range(0, 13):
        for z in range(0, 11):
            roll = (x * 7 + z * 13) % 17
            if roll < 6:
                v.set(x, 0, z, "minecraft:grass_block", snowy="false")
            elif roll < 11:
                v.set(x, 0, z, "minecraft:coarse_dirt")
            elif roll < 14:
                v.set(x, 0, z, "minecraft:gravel")
            else:
                v.set(x, 0, z, "minecraft:dirt")

    # ---- 木地板
    v.box(RIDGE_X - 2, 1, Z0 + 1, RIDGE_X + 2, 1, Z1 - 1, "minecraft:spruce_planks")

    # ---- 帆布 A 字：y=2 宽 7、y=3 宽 5、y=4 宽 3，脊梁在 y=4 中线
    for y, half in ((2, 3), (3, 2), (4, 1)):
        for z in range(Z0, Z1 + 1):
            for x in (RIDGE_X - half, RIDGE_X + half):
                v.set(x, y, z, "minecraft:white_wool" if (y + z) % 2 else "minecraft:light_gray_wool")
            if z in (Z0, Z1):
                for x in range(RIDGE_X - half, RIDGE_X + half + 1):
                    v.set(x, y, z, "minecraft:white_wool" if (y + x) % 2 else "minecraft:light_gray_wool")
    # 脊梁
    for z in range(Z0, Z1 + 1):
        v.set(RIDGE_X, 4, z, "minecraft:stripped_spruce_log", axis="z")
    # 门洞（正面）
    for y in (2, 3):
        for x in (RIDGE_X - 1, RIDGE_X, RIDGE_X + 1):
            v.set(x, y, Z1, AIR)
    # 四角撑杆
    for (px, pz) in ((RIDGE_X - 3, Z0), (RIDGE_X + 3, Z0), (RIDGE_X - 3, Z1), (RIDGE_X + 3, Z1)):
        v.set(px, 1, pz, "minecraft:stripped_spruce_log", axis="y")
        v.set(px, 2, pz, "minecraft:stripped_spruce_log", axis="y")
    # 帐篷内
    v.set(4, 2, 4, "minecraft:red_bed", facing="north", part="foot", occupied="false")
    v.set(4, 2, 3, "minecraft:red_bed", facing="north", part="head", occupied="false")
    v.set(8, 2, 7, "minecraft:crafting_table")
    v.set(RIDGE_X, 3, 5, "minecraft:lantern", hanging="true")

    # ---- 营地：营火 + 原木凳 + 补给
    v.set(10, 1, 6, "minecraft:campfire", facing="north", lit="true", signal_fire="false")
    v.set(9, 1, 7, "minecraft:spruce_log", axis="x")
    v.set(11, 1, 7, "minecraft:spruce_log", axis="x")
    v.set(10, 1, 3, "minecraft:chest", facing="west", type="single", waterlogged="false")
    v.set(11, 1, 4, "minecraft:barrel", facing="up", open="false")
    # 照明：营火 + 火把
    v.set(1, 1, 5, "minecraft:torch")
    # 灌木点缀
    v.set(2, 1, 8, "minecraft:sweet_berry_bush", age="2")
    v.set(11, 1, 9, "minecraft:sweet_berry_bush", age="1")
    # 入口帆布帘 + 地垫
    v.set(RIDGE_X - 1, 3, Z1, "minecraft:white_carpet", waterlogged="false")
    v.set(RIDGE_X, 3, Z1, "minecraft:white_carpet", waterlogged="false")
    v.set(RIDGE_X + 1, 3, Z1, "minecraft:white_carpet", waterlogged="false")
    for x in (RIDGE_X - 1, RIDGE_X, RIDGE_X + 1):
        v.set(x, 1, Z1 + 1, "minecraft:white_carpet", waterlogged="false")
    # 四角拉索
    for (px, pz) in ((RIDGE_X - 3, Z0), (RIDGE_X + 3, Z0), (RIDGE_X - 3, Z1), (RIDGE_X + 3, Z1)):
        v.set(px, 1, pz - 1 if pz == Z0 else pz + 1, "minecraft:chain", axis="y", waterlogged="false")
    # 门口灯杆
    v.set(12, 1, Z1 + 1, "minecraft:oak_fence")
    v.set(12, 2, Z1 + 1, "minecraft:oak_fence")
    v.set(12, 3, Z1 + 1, "minecraft:lantern", hanging="true")
    return v


# ------------------------------------------------------------------ 2. 矿洞入口
def mine_entrance() -> Voxel:
    v = Voxel()
    W, D, H = 17, 14, 15

    # ---- 1) 山体：前高后低的崖壁，边缘做圆角
    for x in range(W):
        for z in range(D):
            base_h = H - 2 - int(z * 0.62)
            if x < 2 or x > W - 3:
                base_h -= 3
            elif x < 4 or x > W - 5:
                base_h -= 1
            base_h += ((x * 7 + z * 13) % 3) - 1      # 起伏，避免整齐阶梯
            base_h = max(3, base_h)
            for y in range(base_h + 1):
                roll = (x * 31 + y * 17 + z * 7) % 23
                if y == base_h:
                    block = "minecraft:grass_block"
                    kwargs = {"snowy": "false"}
                elif y >= base_h - 2:
                    block = "minecraft:dirt"
                    kwargs = {}
                elif roll < 6:
                    block = "minecraft:tuff"
                    kwargs = {}
                elif roll < 10:
                    block = "minecraft:andesite"
                    kwargs = {}
                elif roll < 14:
                    block = "minecraft:stone"
                    kwargs = {}
                else:
                    block = "minecraft:stone"
                    kwargs = {}
                v.set(x, y, z, block, **kwargs)

    # ---- 2) 掏洞：1 格内凹 + 3 宽 × 3 高平巷 + 尽头房间
    for x in range(6, 11):
        for y in range(1, 5):
            v.set(x, y, 0, AIR)                 # 洞口内凹
    for z in range(1, 11):
        for x in range(7, 10):
            for y in range(1, 4):
                v.set(x, y, z, AIR)
    for z in range(9, 13):
        for x in range(5, 12):
            for y in range(1, 5):
                v.set(x, y, z, AIR)

    # ---- 3) 门框与支护
    for (px, pz) in ((6, 0), (10, 0)):
        for y in range(1, 5):
            v.set(px, y, pz, "minecraft:stripped_dark_oak_log", axis="y")
    for x in range(6, 11):
        v.set(x, 4, 0, "minecraft:stripped_dark_oak_log", axis="x")
    for px in (6, 10):
        for y in range(1, 4):
            v.set(px, y, 4, "minecraft:dark_oak_log", axis="y")
            v.set(px, y, 8, "minecraft:dark_oak_log", axis="y")
    for x in range(6, 11):
        v.set(x, 4, 4, "minecraft:dark_oak_log", axis="x")
        v.set(x, 4, 8, "minecraft:dark_oak_log", axis="x")

    # ---- 4) 洞内：轨道、照明、战利品
    for z in range(1, 12):
        v.set(8, 1, z, "minecraft:rail", shape="north_south", waterlogged="false")
    v.set(8, 3, 2, "minecraft:lantern", hanging="true")
    v.set(8, 3, 6, "minecraft:lantern", hanging="true")
    v.set(8, 4, 11, "minecraft:lantern", hanging="true")
    v.set(10, 1, 11, "minecraft:chest", facing="west", type="single", waterlogged="false")
    v.set(6, 1, 11, "minecraft:barrel", facing="up", open="false")
    v.set(6, 1, 10, "minecraft:crafting_table")

    # ---- 5) 洞口外侧：碎石堆 + 木牌位
    v.set(5, 1, 0, "minecraft:cobblestone")
    v.set(11, 1, 0, "minecraft:cobblestone")
    v.set(5, 2, 0, "minecraft:cobblestone_wall")
    v.set(11, 2, 0, "minecraft:cobblestone_wall")
    v.set(8, 3, 0, "minecraft:lantern", hanging="true")

    # ---- 6) 坡脚碎石裙边：弱化山体台阶感
    for x in range(W):
        for z in range(D):
            top = None
            for y in range(H - 1, -1, -1):
                if v.get(x, y, z):
                    top = y
                    break
            if top is not None and top <= 2:
                roll = (x * 3 + z * 5) % 4
                if roll == 0:
                    v.set(x, top + 1, z, "minecraft:cobblestone")
                elif roll == 1:
                    v.set(x, top + 1, z, "minecraft:gravel")
    # ---- 7) 轨道延伸到洞外
    for z in range(-3, 0):
        v.set(8, 0, z, "minecraft:gravel")
        v.set(8, 1, z, "minecraft:rail", shape="north_south", waterlogged="false")
        if z == -2:
            v.set(7, 1, z, "minecraft:cobblestone")
            v.set(9, 1, z, "minecraft:cobblestone")
    return v


# ------------------------------------------------------------------ 4. 废弃前哨
def abandoned_outpost() -> Voxel:
    v = Voxel()
    W, H, D = 15, 10, 15

    # ---- 地面
    for x in range(W):
        for z in range(D):
            roll = (x * 11 + z * 7) % 13
            v.set(x, 0, z, "minecraft:grass_block", snowy="false") if roll < 7 else v.set(x, 0, z, "minecraft:coarse_dirt")

    # ---- 围墙（石砖，带缺口）
    for x in range(2, 13):
        for z in (2, 12):
            for y in range(1, 4):
                if (x * 3 + y * 5) % 7 != 0:
                    v.set(x, y, z, "minecraft:stone_bricks")
    for z in range(2, 13):
        for x in (2, 12):
            for y in range(1, 4):
                if (z * 3 + y * 5) % 7 != 0:
                    v.set(x, y, z, "minecraft:stone_bricks")
    # 墙顶压条与破损
    for x in range(2, 13):
        for z in (2, 12):
            v.set(x, 4, z, "minecraft:stone_brick_slab", type="bottom", waterlogged="false")
    for z in range(2, 13):
        for x in (2, 12):
            v.set(x, 4, z, "minecraft:stone_brick_slab", type="bottom", waterlogged="false")
    # 大门（正面中间留门 + 木门框）
    for y in range(1, 4):
        v.set(6, y, 12, "minecraft:stripped_dark_oak_log", axis="y")
        v.set(9, y, 12, "minecraft:stripped_dark_oak_log", axis="y")
        v.set(7, y, 12, AIR)
        v.set(8, y, 12, AIR)
    v.set(7, 1, 12, "minecraft:dark_oak_fence")   # 半掩的门
    v.set(8, 2, 12, "minecraft:dark_oak_fence")

    # ---- 瞭望塔（角落）
    for y in range(1, 8):
        for (x, z) in ((10, 3), (12, 3), (10, 5), (12, 5)):
            v.set(x, y, z, "minecraft:stripped_dark_oak_log", axis="y")
    for y in (4, 7):
        for x in range(10, 13):
            for z in range(3, 6):
                if x in (10, 12) or z in (3, 5):
                    v.set(x, y, z, "minecraft:spruce_planks")
    # 塔顶棚与灯具
    for x in range(10, 13):
        for z in range(3, 6):
            v.set(x, 8, z, "minecraft:spruce_planks")
    v.set(11, 7, 4, "minecraft:lantern", hanging="true")
    # 梯子
    for y in range(1, 7):
        v.set(11, y, 3, "minecraft:ladder", facing="south", waterlogged="false")
    # 塔顶风车（生成即转）：立柱 + 风车轴承
    v.set(11, 9, 4, "minecraft:stripped_dark_oak_log", axis="y")
    v.windmill_wheel(11, 10, 4, facing="south", radius=2, sail="create:white_sail")
    # 残破旗帜（挂在旗杆上）
    v.set(3, 4, 3, "minecraft:oak_fence")
    v.set(3, 4, 4, "minecraft:white_wall_banner", facing="south")

    # ---- 营地遗迹
    v.set(5, 1, 6, "minecraft:campfire", facing="north", lit="false", signal_fire="false")
    v.set(4, 1, 7, "minecraft:spruce_log", axis="x")
    v.set(6, 1, 5, "minecraft:chest", facing="west", type="single", waterlogged="false")
    v.set(7, 1, 7, "minecraft:barrel", facing="up", open="false")
    v.set(4, 1, 4, "minecraft:crafting_table")
    v.set(3, 1, 9, "minecraft:cobweb")
    v.set(11, 1, 9, "minecraft:cobweb")
    # 旗帜杆（无旗帜，只剩杆）
    v.set(3, 1, 3, "minecraft:oak_fence")
    v.set(3, 2, 3, "minecraft:oak_fence")
    v.set(3, 3, 3, "minecraft:oak_fence")
    return v


# ------------------------------------------------------------------ 5. 信号塔
def signal_tower() -> Voxel:
    v = Voxel()
    W, H, D = 9, 24, 9
    CX, CZ = 4, 4

    # ---- 基座
    for x in range(1, 8):
        for z in range(1, 8):
            v.set(x, 0, z, "minecraft:stone_bricks")
    for x in range(2, 7):
        for z in range(2, 7):
            v.set(x, 1, z, "minecraft:stone_bricks")
            v.set(x, 2, z, "minecraft:chiseled_stone_bricks")
    # 台阶入口
    v.set(CX, 1, 0, "minecraft:stone_brick_stairs", facing="south", half="bottom", shape="straight", waterlogged="false")
    # ---- 塔身桁架
    for y in range(3, 18):
        for (x, z) in ((CX - 1, CZ - 1), (CX + 1, CZ - 1), (CX - 1, CZ + 1), (CX + 1, CZ + 1)):
            if (y % 4) != 0:
                v.set(x, y, z, "minecraft:iron_bars", north="false", south="false", east="false", west="false", waterlogged="false")
        if y % 4 == 0:
            for x in range(CX - 1, CX + 2):
                v.set(x, y, CZ - 1, "minecraft:polished_andesite")
                v.set(x, y, CZ + 1, "minecraft:polished_andesite")
            for z in range(CZ - 1, CZ + 2):
                v.set(CX - 1, y, z, "minecraft:polished_andesite")
                v.set(CX + 1, y, z, "minecraft:polished_andesite")
    # ---- 平台
    for x in range(CX - 2, CX + 3):
        for z in range(CZ - 2, CZ + 3):
            v.set(x, 18, z, "minecraft:spruce_planks")
    for (x, z) in ((CX - 2, CZ - 2), (CX + 2, CZ - 2), (CX - 2, CZ + 2), (CX + 2, CZ + 2)):
        v.set(x, 19, z, "minecraft:oak_fence")
        v.set(x, 20, z, "minecraft:oak_fence")
    # ---- 顶部天线与信号灯
    for y in range(19, 23):
        v.set(CX, y, CZ, "minecraft:iron_bars", north="false", south="false", east="false", west="false", waterlogged="false")
    v.set(CX, 23, CZ, "minecraft:lantern", hanging="false", waterlogged="false")
    v.set(CX - 1, 19, CZ, "minecraft:lantern", hanging="true")
    v.set(CX + 1, 19, CZ, "minecraft:lantern", hanging="true")
    # 塔身中部检修平台
    for x in range(CX - 1, CX + 2):
        for z in (CZ - 1, CZ + 1):
            v.set(x, 10, z, "minecraft:dark_oak_slab", type="bottom", waterlogged="false")
    # 底部门（半开）
    v.set(CX, 2, CZ + 2, "minecraft:spruce_door", facing="south", half="lower", hinge="left", open="false", powered="false")
    v.set(CX, 3, CZ + 2, "minecraft:spruce_door", facing="south", half="upper", hinge="left", open="false", powered="false")

    # ---- 优化：四角框柱（让桁架更"工程感"）
    for y in range(3, 18):
        for (x, z) in ((CX - 1, CZ - 1), (CX + 1, CZ - 1), (CX - 1, CZ + 1), (CX + 1, CZ + 1)):
            if y % 4 != 0:
                v.set(x, y, z, "minecraft:polished_andesite")
    # ---- 优化：平台护栏（四面留缺口当入口）
    for x in range(CX - 2, CX + 3):
        for z in (CZ - 2, CZ + 2):
            if (x + z) % 3 != 0:
                v.set(x, 20, z, "minecraft:oak_fence")
    for z in range(CZ - 1, CZ + 2):
        for x in (CX - 2, CX + 2):
            v.set(x, 20, z, "minecraft:oak_fence")
    # ---- 优化：顶部信标灯
    v.set(CX, 18, CZ - 1, "minecraft:redstone_lamp", lit="true")
    # ---- 优化：塔基碎石
    for (x, z) in ((0, 0), (8, 0), (0, 8), (8, 8), (2, 0), (6, 8)):
        v.set(x, 0, z, "minecraft:cobblestone")
        v.set(x, 1, z, "minecraft:mossy_cobblestone")
    return v


# ------------------------------------------------------------------ 6. 旧码头
def old_dock() -> Voxel:
    v = Voxel()
    W, H, D = 18, 10, 22

    # ---- 岸线：砂砾 + 碎石 + 少量草
    for x in range(W):
        for z in range(0, 6):
            roll = (x * 7 + z * 11) % 13
            if roll < 5:
                v.set(x, 0, z, "minecraft:gravel")
            elif roll < 8:
                v.set(x, 0, z, "minecraft:sand")
            elif roll < 10:
                v.set(x, 0, z, "minecraft:cobblestone")
            else:
                v.set(x, 0, z, "minecraft:grass_block", snowy="false")

    # ---- 栈桥：高出水面 2 格的木板 + 木桩
    for z in range(3, 21):
        for x in range(5, 12):
            v.set(x, 2, z, "minecraft:spruce_planks")
        if z % 3 == 1:
            v.set(5, 1, z, "minecraft:stripped_dark_oak_log", axis="y")
            v.set(11, 1, z, "minecraft:stripped_dark_oak_log", axis="y")
            v.set(5, 0, z, "minecraft:stripped_dark_oak_log", axis="y")
            v.set(11, 0, z, "minecraft:stripped_dark_oak_log", axis="y")
    # 栏杆（断续，年久失修）
    for z in range(4, 20):
        if z % 4 != 0:
            v.set(12, 3, z, "minecraft:oak_fence")
        if z % 5 != 0:
            v.set(4, 3, z, "minecraft:oak_fence")

    # ---- 起重机
    for y in range(3, 8):
        v.set(7, y, 6, "minecraft:stripped_dark_oak_log", axis="y")
    v.line(7, 7, 6, 11, 8, 10, "minecraft:stripped_dark_oak_log", axis="x")
    for y in (6, 5, 4):
        v.set(11, y, 10, "minecraft:chain", axis="y", waterlogged="false")
    v.set(11, 3, 10, "minecraft:barrel", facing="up", open="false")

    # ---- 码头上的物资
    v.set(11, 3, 17, "minecraft:chest", facing="west", type="single", waterlogged="false")
    v.set(9, 3, 18, "minecraft:barrel", facing="up", open="false")
    v.set(6, 3, 16, "minecraft:crafting_table")
    v.set(6, 3, 19, "minecraft:lantern", hanging="false", waterlogged="false")

    # ---- 搁浅的小船（只余船骨）
    for z in range(12, 17):
        for x in range(13, 17):
            if x in (13, 16) or z in (12, 16):
                if (x + z) % 3 != 0:
                    v.set(x, 1, z, "minecraft:spruce_planks")
    v.set(14, 1, 13, "minecraft:spruce_planks")
    v.set(15, 1, 13, "minecraft:spruce_planks")

    # ---- 系船柱与缆绳
    for (px, pz) in ((5, 5), (11, 12), (5, 19)):
        v.set(px, 3, pz, "minecraft:stripped_dark_oak_log", axis="y")
        v.set(px, 4, pz, "minecraft:stripped_dark_oak_log", axis="y")
        for y in (3, 2):
            v.set(px + (1 if px == 5 else -1), y, pz, "minecraft:chain", axis="y", waterlogged="false")
    # 岸线过渡：沙 → 砾石 → 草
    for x in range(W):
        for z in range(5, 7):
            if (x + z) % 3 == 0:
                v.set(x, 0, z, "minecraft:gravel")
            elif (x + z) % 3 == 1:
                v.set(x, 0, z, "minecraft:sand")
    # 货堆
    v.set(10, 3, 19, "minecraft:barrel", facing="up", open="false")
    v.set(9, 3, 19, "minecraft:barrel", facing="up", open="false")
    v.set(10, 4, 19, "minecraft:barrel", facing="up", open="false")
    v.set(6, 3, 14, "minecraft:chest", facing="west", type="single", waterlogged="false")
    return v


# ------------------------------------------------------------------ 7. 废弃直升机停机坪
def abandoned_helipad() -> Voxel:
    v = Voxel()
    W, H, D = 19, 14, 19

    # ---- 地面：荒废的碎石/泥土/草
    for x in range(W):
        for z in range(D):
            roll = (x * 7 + z * 13) % 17
            if roll < 6:
                v.set(x, 0, z, "minecraft:gravel")
            elif roll < 11:
                v.set(x, 0, z, "minecraft:coarse_dirt")
            elif roll < 14:
                v.set(x, 0, z, "minecraft:grass_block", snowy="false")
            else:
                v.set(x, 0, z, "minecraft:dirt")

    # ---- 停机坪：13×13 台面 + 石基（只保留坪面本身）
    for x in range(2, 15):
        for z in range(2, 15):
            v.set(x, 1, z, "minecraft:smooth_stone")
            roll = (x * 11 + z * 7) % 23
            if roll < 12:
                block = "minecraft:light_gray_concrete"
            elif roll < 18:
                block = "minecraft:light_gray_concrete_powder"
            elif roll < 21:
                block = "minecraft:gray_concrete"
            else:
                block = "minecraft:light_gray_concrete"
            v.set(x, 2, z, block)

    # ---- 中央 H 标记
    for z in range(5, 12):
        v.set(6, 2, z, "minecraft:white_concrete")
        v.set(10, 2, z, "minecraft:white_concrete")
    for x in range(6, 11):
        v.set(x, 2, 8, "minecraft:white_concrete")
    # 外圈黄线（斑驳）
    for i in range(3, 14):
        if i % 4 != 0:
            v.set(i, 2, 3, "minecraft:yellow_concrete")
            v.set(i, 2, 13, "minecraft:yellow_concrete")
            v.set(3, 2, i, "minecraft:yellow_concrete")
            v.set(13, 2, i, "minecraft:yellow_concrete")

    # ---- 少量破损与杂草（不超过 6 处）
    for (x, z) in ((2, 2), (14, 2), (2, 14), (14, 14)):
        v.set(x, 2, z, "minecraft:cracked_stone_bricks")
    for (x, z) in ((4, 4), (12, 11)):
        v.set(x, 2, z, "minecraft:moss_block")
        v.set(x, 3, z, "minecraft:short_grass")
    return v


# ------------------------------------------------------------------ 8. 小鸡雕像
def chicken_statue() -> Voxel:
    v = Voxel()
    W, H, D = 11, 26, 11
    CX, CZ = 5, 5

    # ---- 地面
    for x in range(W):
        for z in range(D):
            roll = (x * 5 + z * 11) % 13
            v.set(x, 0, z, "minecraft:grass_block", snowy="false") if roll < 8 else v.set(x, 0, z, "minecraft:coarse_dirt")

    # ---- 底座：9×9×5 全实心（不中空），下界合金块嵌在石砖内部
    for x in range(1, 10):
        for z in range(1, 10):
            for y in range(1, 6):
                v.set(x, y, z, "minecraft:stone_bricks")
    # 藏宝：下界合金块直接嵌进实心石砖里，必须挖进去才能拿到
    v.set(CX, 2, CZ, "minecraft:netherite_block")
    # 夹层暗示：正面一块裂缝石砖 + 上方 chiseled
    v.set(CX, 1, 9, "minecraft:cracked_stone_bricks")
    v.set(CX, 5, 9, "minecraft:chiseled_stone_bricks")
    # 底座收边（仅装饰，不影响承重）
    for x in range(1, 10):
        for z in range(1, 10):
            if (x in (1, 9) or z in (1, 9)) and (x + z) % 3 == 0:
                v.set(x, 5, z, "minecraft:chiseled_stone_bricks")

    # ---- 雕像：腿（y=6..8，正下方 y=5 是实心底座）
    for x in (CX - 1, CX + 1):
        for y in range(6, 9):
            v.set(x, y, CZ, "minecraft:orange_terracotta")
    # ---- 腹部：把腿和身体连起来（y=9..10 中心区域实心）
    for x in range(CX - 1, CX + 2):
        for z in range(CZ - 1, CZ + 2):
            v.set(x, 9, z, "minecraft:white_wool")
    for x in range(CX - 1, CX + 2):
        v.set(x, 10, CZ, "minecraft:white_wool")
    # ---- 身体（椭球壳）
    for x in range(CX - 3, CX + 4):
        for y in range(9, 16):
            for z in range(CZ - 3, CZ + 4):
                dx = (x - CX) / 3.4
                dy = (y - 12) / 3.6
                dz = (z - CZ) / 3.2
                d = dx * dx + dy * dy + dz * dz
                if 0.55 <= d <= 1.05:
                    v.set(x, y, z, "minecraft:white_wool")
    # ---- 翅膀
    for y in range(10, 14):
        for z in range(CZ - 2, CZ + 2):
            v.set(CX - 4, y, z, "minecraft:light_gray_wool")
            v.set(CX + 4, y, z, "minecraft:light_gray_wool")
    # ---- 尾羽
    for y in range(11, 15):
        v.set(CX, y, CZ - 4, "minecraft:white_wool")
        if y < 14:
            v.set(CX - 1, y, CZ - 4, "minecraft:light_gray_wool")
            v.set(CX + 1, y, CZ - 4, "minecraft:light_gray_wool")
    # ---- 脖子与头
    for y in range(15, 18):
        for x in range(CX - 1, CX + 2):
            for z in range(CZ - 1, CZ + 2):
                v.set(x, y, z, "minecraft:white_wool")
    # 喙
    v.set(CX, 16, CZ + 2, "minecraft:yellow_concrete")
    v.set(CX, 16, CZ + 3, "minecraft:yellow_concrete")
    v.set(CX, 15, CZ + 2, "minecraft:yellow_concrete")
    # 眼睛
    v.set(CX - 1, 17, CZ + 2, "minecraft:black_concrete")
    v.set(CX + 1, 17, CZ + 2, "minecraft:black_concrete")
    # 鸡冠与肉垂
    for x in range(CX - 1, CX + 2):
        v.set(x, 19, CZ, "minecraft:red_concrete")
    v.set(CX, 20, CZ, "minecraft:red_concrete")
    v.set(CX, 14, CZ + 2, "minecraft:red_concrete")
    v.set(CX, 13, CZ + 2, "minecraft:red_concrete")
    return v


DESIGNS = {
    "camping_tent": camping_tent,
    "mine_entrance": mine_entrance,
    "abandoned_outpost": abandoned_outpost,
    "signal_tower": signal_tower,
    "old_dock": old_dock,
    "abandoned_helipad": abandoned_helipad,
    "chicken_statue": chicken_statue,
}


if __name__ == "__main__":
    os.makedirs(NBT_DIR, exist_ok=True)
    os.makedirs(IMG_DIR, exist_ok=True)
    for name, fn in DESIGNS.items():
        vox = fn()
        size, nbt_path, img_path = _save(vox, name, scale=7 if name == "camping_tent" else 6)
        print(f"{name}: size={size} blocks={len(vox.cells)} -> {os.path.basename(nbt_path)} / {os.path.basename(img_path)}")
