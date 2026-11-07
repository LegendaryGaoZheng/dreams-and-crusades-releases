# -*- coding: utf-8 -*-
import os, re, hashlib

from pathlib import Path
import argparse
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workflow import legacy_quest_chapters

parser = argparse.ArgumentParser(description="Historical quest draft tool. Use a fresh staged copy.")
parser.add_argument("--chapters", required=True)
BASE = legacy_quest_chapters(parser.parse_args().chapters)

def oid(name):
    return hashlib.md5(name.encode("utf-8")).hexdigest()[:16].upper()

def task_text(t, idx):
    tid = oid("t%s" % idx)
    if t[0] == "check":
        return "\t\t\t\t{\n\t\t\t\t\tid: \"%s\"\n\t\t\t\t\ttype: \"checkmark\"\n\t\t\t\t}" % tid
    if t[0] == "item":
        item, count = t[1], t[2]
        consume = t[3] if len(t) > 3 else False
        lines = ["\t\t\t\t{"]
        if consume:
            lines.append("\t\t\t\t\tconsume_items: true")
        lines.append("\t\t\t\t\tcount: %d" % count)
        lines.append("\t\t\t\t\tid: \"%s\"" % tid)
        lines.append("\t\t\t\t\titem: \"%s\"" % item)
        lines.append("\t\t\t\t\ttype: \"item\"")
        lines.append("\t\t\t\t}")
        return "\n".join(lines)
    if t[0] == "adv":
        return ("\t\t\t\t{\n\t\t\t\t\tadvancement: \"%s\"\n\t\t\t\t\tcriterion: \"\"\n"
                "\t\t\t\t\tid: \"%s\"\n\t\t\t\t\ttype: \"advancement\"\n\t\t\t\t}") % (t[1], tid)
    raise ValueError(t)

def reward_text(r, idx):
    rid = oid("r%s" % idx)
    if r[0] == "xp":
        return "\t\t\t\t{\n\t\t\t\t\tid: \"%s\"\n\t\t\t\t\ttype: \"xp\"\n\t\t\t\t\txp: %d\n\t\t\t\t}" % (rid, r[1])
    if r[0] == "item":
        return ("\t\t\t\t{\n\t\t\t\t\tcount: %d\n\t\t\t\t\tid: \"%s\"\n\t\t\t\t\titem: \"%s\"\n"
                "\t\t\t\t\ttype: \"item\"\n\t\t\t\t}") % (r[2], rid, r[1])
    raise ValueError(r)

def quest_block(name, title, desc, icon, tasks, rewards, shape, size, x, y, deps=(), repeat=None):
    qid = oid(name)
    L = ["\t\t{"]
    if deps:
        L.append("\t\t\tdependencies: [" + ", ".join('"%s"' % oid(d) for d in deps) + "]")
    L.append("\t\t\tdescription: [" + ", ".join('"%s"' % d for d in desc) + "]")
    L.append("\t\t\ticon: \"%s\"" % icon)
    L.append("\t\t\tid: \"%s\"" % qid)
    if repeat:
        L.append("\t\t\tcan_repeat: true")
        L.append("\t\t\trepeat_cooldown: %d" % repeat)
    L.append("\t\t\tshape: \"%s\"" % shape)
    L.append("\t\t\tsize: %.1fd" % size)
    L.append("\t\t\tsubtitle: \"%s\"" % title)
    L.append("\t\t\trewards: [")
    for i, r in enumerate(rewards):
        L.append(reward_text(r, qid + str(i)))
    L.append("\t\t\t]")
    L.append("\t\t\ttasks: [")
    for i, t in enumerate(tasks):
        L.append(task_text(t, qid + str(i)))
    L.append("\t\t\t]")
    L.append("\t\t\ttitle: \"%s\"" % title)
    L.append("\t\t\tx: %.1fd" % x)
    L.append("\t\t\ty: %.1fd" % y)
    L.append("\t\t}")
    return qid, "\n".join(L)

def write_chapter(fname, icon, order, title, subtitle, blocks):
    cid = oid("chapter:" + fname)
    content = ("{\n\ndefault_hide_dependency_lines: false\n\tdefault_quest_shape: \"\"\n"
               "\tfilename: \"%s\"\n\tgroup: \"\"\n\ticon: \"%s\"\n\tid: \"%s\"\n\timages: [ ]\n"
               "\torder_index: %d\n\tquest_links: [ ]\n\tquests: [\n%s\n\t]\n\tsubtitle: [\"%s\"]\n"
               "\ttitle: \"%s\"\n}\n") % (fname, icon, cid, order, "\n".join(blocks), subtitle, title)
    with open(os.path.join(BASE, fname + ".snbt"), "w", encoding="utf-8") as f:
        f.write(content)

# ---------------- farmer ----------------
F = []
def fq(name, title, desc, icon, tasks, rewards, shape, size, x, y, deps=(), repeat=None):
    qid, block = quest_block(name, title, [desc], icon, tasks, rewards, shape, size, x, y, deps, repeat)
    F.append(block)
    return name

fq("farmer:board", "砧板与刀", "先做砧板（砍树+木板）和燧石刀，农夫乐事的起点。", "farmersdelight:cutting_board",
   [("item", "farmersdelight:cutting_board", 1), ("item", "farmersdelight:flint_knife", 1)],
   [("xp", 30), ("item", "farmersdelight:flint_knife", 1)], "hexagon", 2.5, 0.0, 0.0)
fq("farmer:knife", "更快的刀", "铁刀比燧石刀耐用，切菜也更快。", "farmersdelight:iron_knife",
   [("item", "farmersdelight:iron_knife", 1)], [("xp", 20)], "circle", 1.5, 4.0, -3.0, ["farmer:board"])
fq("farmer:pot", "厨锅", "厨锅是热菜的核心，放在炉子上用。", "farmersdelight:cooking_pot",
   [("item", "farmersdelight:cooking_pot", 1)], [("xp", 40), ("item", "minecraft:bowl", 8)], "square", 2.0, 0.0, -3.0, ["farmer:board"])
fq("farmer:stove", "炉灶", "炉灶可以同时烧菜和当燃料灶台。", "farmersdelight:stove",
   [("item", "farmersdelight:stove", 1)], [("xp", 30)], "circle", 1.5, -4.0, -3.0, ["farmer:pot"])
fq("farmer:skillet", "煎锅", "煎锅适合做汉堡肉饼和煎蛋。", "farmersdelight:skillet",
   [("item", "farmersdelight:skillet", 1)], [("xp", 30)], "circle", 1.5, 4.0, -6.0, ["farmer:pot"])
fq("farmer:tomato", "番茄", "番茄种子可以在野外或村庄找到。", "farmersdelight:tomato",
   [("item", "farmersdelight:tomato", 4)], [("xp", 20), ("item", "farmersdelight:tomato_seeds", 4)], "square", 2.0, 0.0, -6.0, ["farmer:pot"])
fq("farmer:onion", "洋葱", "洋葱是炖菜和汤的基础。", "farmersdelight:onion",
   [("item", "farmersdelight:onion", 4)], [("xp", 20)], "circle", 1.5, 4.0, -9.0, ["farmer:tomato"])
fq("farmer:cabbage", "卷心菜", "卷心菜可以做成卷心菜卷。", "farmersdelight:cabbage",
   [("item", "farmersdelight:cabbage", 4)], [("xp", 20)], "circle", 1.5, 8.0, -6.0, ["farmer:tomato"])
fq("farmer:rice", "稻米", "稻米需要水边种植，是炒饭的主料。", "farmersdelight:rice",
   [("item", "farmersdelight:rice", 8)], [("xp", 25), ("item", "farmersdelight:rice_panicle", 4)], "square", 2.0, -4.0, -6.0, ["farmer:pot"])
fq("farmer:soup", "蔬菜汤", "一锅热汤，回复效果不错。", "farmersdelight:vegetable_soup",
   [("item", "farmersdelight:vegetable_soup", 1)], [("xp", 40)], "square", 2.0, -4.0, -9.0, ["farmer:rice"])
fq("farmer:stew", "牛肉炖菜", "牛肉 + 蔬菜，硬菜。", "farmersdelight:beef_stew",
   [("item", "farmersdelight:beef_stew", 1)], [("xp", 50), ("item", "farmersdelight:beef_stew", 1)], "square", 2.0, 0.0, -9.0, ["farmer:onion"])
fq("farmer:friedrice", "炒饭", "稻米 + 鸡蛋，军粮首选。", "farmersdelight:fried_rice",
   [("item", "farmersdelight:fried_rice", 4)], [("xp", 50)], "gear", 2.2, 4.0, -12.0, ["farmer:rice"])
fq("farmer:burger", "汉堡", "面包 + 肉饼 + 蔬菜。", "farmersdelight:hamburger",
   [("item", "farmersdelight:hamburger", 2)], [("xp", 40)], "circle", 1.5, 0.0, -12.0, ["farmer:stew"])
fq("farmer:roastchicken", "烤鸡盛宴", "整只烤鸡，适合宴请。", "farmersdelight:roast_chicken_block",
   [("item", "farmersdelight:roast_chicken_block", 1)], [("xp", 80), ("item", "farmersdelight:roast_chicken_block", 1)], "gear", 2.2, 8.0, -9.0, ["farmer:cabbage"])
fq("farmer:ham", "蜜汁火腿", "节日级别的硬菜。", "farmersdelight:honey_glazed_ham_block",
   [("item", "farmersdelight:honey_glazed_ham_block", 1)], [("xp", 80)], "circle", 1.5, 8.0, -12.0, ["farmer:roastchicken"])
fq("farmer:cider", "苹果酒", "苹果酿的饮料，恢复不错。", "farmersdelight:apple_cider",
   [("item", "farmersdelight:apple_cider", 1)], [("xp", 30)], "circle", 1.5, -8.0, -6.0, ["farmer:pot"])
fq("farmer:dogfood", "狗粮", "用肉和谷物做狗粮，宠物分支的必需品。", "farmersdelight:dog_food",
   [("item", "farmersdelight:dog_food", 4)], [("xp", 25)], "circle", 1.5, -8.0, -9.0, ["farmer:stew"])
fq("farmer:horsefeed", "马饲料", "马饲料能加速马匹恢复。", "farmersdelight:horse_feed",
   [("item", "farmersdelight:horse_feed", 4)], [("xp", 25)], "circle", 1.5, -4.0, -12.0, ["farmer:dogfood"])
fq("farmer:contract", "军粮合同", "交 16 份熟饭，换兵员卷轴。在任务书里点击提交。", "farmersdelight:cooked_rice",
   [("item", "farmersdelight:cooked_rice", 16, True)],
   [("xp", 60), ("item", "hundred_years_war:scroll_shieldman", 1)], "pentagon", 1.8, 4.0, -15.0, ["farmer:friedrice"], 1800)
fq("farmer:feast", "丰收宴", "摆一桌菜：烤鸡、火腿、汤和酒。", "minecraft:cake",
   [("check",)], [("xp", 150), ("item", "hundred_years_war:scroll_archer", 1)], "heart", 2.5, 0.0, -15.0, ["farmer:roastchicken", "farmer:ham", "farmer:soup"])
write_chapter("farmer", "farmersdelight:cooking_pot", 7, "农夫乐事", "从砧板到丰收宴", F)

# ---------------- pets ----------------
P = []
def pq(name, title, desc, icon, tasks, rewards, shape, size, x, y, deps=(), repeat=None):
    qid, block = quest_block(name, title, [desc], icon, tasks, rewards, shape, size, x, y, deps, repeat)
    P.append(block)
    return name

pq("pets:wolf", "驯服一只狼", "用骨头驯服狼，它会跟着你。", "minecraft:bone",
   [("item", "minecraft:bone", 10), ("adv", "minecraft:husbandry/tame_an_animal")],
   [("xp", 30), ("item", "minecraft:bone", 8)], "hexagon", 2.5, 0.0, 0.0)
pq("pets:wolfarmor", "狼铠", "给狼穿上狼铠，它会更耐打。", "minecraft:wolf_armor",
   [("item", "minecraft:wolf_armor", 1)], [("xp", 40)], "square", 2.0, 4.0, -3.0, ["pets:wolf"])
pq("pets:feed", "喂狗粮", "用农夫乐事的狗粮喂狼。", "farmersdelight:dog_food",
   [("item", "farmersdelight:dog_food", 4)], [("xp", 30)], "square", 2.0, 0.0, -3.0, ["pets:wolf"])
pq("pets:breed", "繁殖狼", "两只驯服的狼可以繁殖。", "minecraft:bone",
   [("adv", "minecraft:husbandry/breed_an_animal")], [("xp", 50)], "square", 2.0, 4.0, -6.0, ["pets:feed"])
pq("pets:cat", "驯服一只猫", "用生鱼驯服猫。", "minecraft:cod",
   [("item", "minecraft:cod", 10)], [("xp", 30)], "square", 2.0, -4.0, -3.0, ["pets:wolf"])
pq("pets:catgift", "猫的礼物", "猫会偶尔给你带礼物。", "minecraft:string",
   [("check",)], [("xp", 30)], "circle", 1.5, -8.0, -6.0, ["pets:cat"])
pq("pets:saddle", "马鞍", "驯服马并装上马鞍。", "minecraft:saddle",
   [("item", "minecraft:saddle", 1)], [("xp", 40)], "circle", 1.5, 0.0, -6.0, ["pets:wolf"])
pq("pets:horsearmor", "马铠", "铁马铠能显著提高马的生存。", "minecraft:iron_horse_armor",
   [("item", "minecraft:iron_horse_armor", 1)], [("xp", 40)], "circle", 1.5, 4.0, -9.0, ["pets:saddle"])
pq("pets:ride", "骑乘", "骑上马跑一段路。", "minecraft:saddle",
   [("check",)], [("xp", 30)], "square", 2.0, 0.0, -9.0, ["pets:saddle"])
pq("pets:horsefeed", "马饲料", "用马饲料恢复马匹。", "farmersdelight:horse_feed",
   [("item", "farmersdelight:horse_feed", 4)], [("xp", 25)], "circle", 1.5, -4.0, -9.0, ["pets:ride"])
pq("pets:warhound", "战犬卷轴", "HYW 的强盗战犬卷轴，部署一只战犬。", "hundred_years_war:scroll_bandit_war_hound_1",
   [("item", "hundred_years_war:scroll_bandit_war_hound_1", 1)],
   [("xp", 60), ("item", "hundred_years_war:scroll_bandit_war_hound_1", 1)], "gear", 2.2, 8.0, -3.0, ["pets:wolf"])
pq("pets:warhound2", "战犬随行", "让战犬跟随你作战。", "hundred_years_war:scroll_bandit_war_hound_1",
   [("check",)], [("xp", 40)], "circle", 1.5, 8.0, -6.0, ["pets:warhound"])
pq("pets:nametag", "给宠物命名", "用命名牌给宠物起个名字。", "minecraft:name_tag",
   [("item", "minecraft:name_tag", 1)], [("xp", 25)], "circle", 1.5, 8.0, -9.0, ["pets:warhound2"])
pq("pets:house", "宠物小屋", "给宠物搭一个有床和食物的小屋。", "minecraft:oak_planks",
   [("check",)], [("xp", 40)], "circle", 1.5, -8.0, -3.0, ["pets:cat"])
pq("pets:zoo", "动物园", "同时拥有狼、猫、马、战犬。", "minecraft:lead",
   [("check",)], [("xp", 150), ("item", "sophisticatedbackpacks:upgrade_base", 1)], "heart", 2.5, 0.0, -12.0, ["pets:breed", "pets:catgift", "pets:warhound2"])
pq("pets:contract", "狗粮合同", "交 16 份狗粮，换背包升级件。在任务书里点击提交。", "farmersdelight:dog_food",
   [("item", "farmersdelight:dog_food", 16, True)],
   [("xp", 50), ("item", "sophisticatedbackpacks:upgrade_base", 1)], "pentagon", 1.8, -4.0, -12.0, ["pets:feed"], 1800)
write_chapter("pets", "minecraft:bone", 8, "宠物", "狼、猫、马与战犬", P)

# ---------------- quark ----------------
Q = []
def qq(name, title, desc, icon, tasks, rewards, shape, size, x, y, deps=(), repeat=None):
    qid, block = quest_block(name, title, [desc], icon, tasks, rewards, shape, size, x, y, deps, repeat)
    Q.append(block)
    return name

qq("quark:slab", "竖半砖", "夸克的竖半砖，建筑细节神器。", "quark:oak_vertical_slab",
   [("item", "quark:oak_vertical_slab", 8)], [("xp", 30)], "hexagon", 2.5, 0.0, 0.0)
qq("quark:hedge", "树篱", "用树篱做花园围墙。", "quark:oak_hedge",
   [("item", "quark:oak_hedge", 8)], [("xp", 30)], "square", 2.0, 4.0, -3.0, ["quark:slab"])
qq("quark:rope", "绳子", "夸克的绳子可以垂直攀爬。", "quark:rope",
   [("item", "quark:rope", 8)], [("xp", 25)], "circle", 1.5, 0.0, -3.0, ["quark:slab"])
qq("quark:frame", "玻璃物品框", "把物品放进玻璃框展示。", "quark:glass_item_frame",
   [("item", "quark:glass_item_frame", 1)], [("xp", 25)], "circle", 1.5, -4.0, -3.0, ["quark:slab"])
qq("quark:pickarang", "Pickarang", "会飞回来的镐子。", "quark:pickarang",
   [("item", "quark:pickarang", 1)], [("xp", 60)], "gear", 2.2, 8.0, -3.0, ["quark:hedge"])
qq("quark:trowel", "Trowel", "快速铺路的工具。", "quark:trowel",
   [("item", "quark:trowel", 1)], [("xp", 30)], "square", 2.0, 4.0, -6.0, ["quark:hedge"])
qq("quark:seedpouch", "种子袋", "自动收集种子的袋子。", "quark:seed_pouch",
   [("item", "quark:seed_pouch", 1)], [("xp", 30)], "circle", 1.5, 0.0, -6.0, ["quark:rope"])
qq("quark:sort", "整理背包", "按 N 整理一次背包（在控制里绑定 Quark 的 Sort Inventory）。", "minecraft:hopper",
   [("check",)], [("xp", 20)], "square", 2.0, -4.0, -6.0, ["quark:frame"])
qq("quark:search", "箱内搜索", "在箱子里用搜索栏找物品。", "minecraft:chest",
   [("check",)], [("xp", 20)], "circle", 1.5, -8.0, -3.0, ["quark:frame"])
qq("quark:transfer", "快速转移", "Shift+点击快速转移整组物品。", "minecraft:chest",
   [("check",)], [("xp", 20)], "circle", 1.5, -8.0, -6.0, ["quark:search"])
qq("quark:restock", "自动补工具", "工具坏了自动从背包补一把。", "minecraft:iron_pickaxe",
   [("check",)], [("xp", 30)], "circle", 1.5, 4.0, -9.0, ["quark:trowel"])
qq("quark:hotbar", "快捷栏切换", "用快捷键切换整排快捷栏。", "minecraft:barrel",
   [("check",)], [("xp", 20)], "circle", 1.5, 0.0, -9.0, ["quark:seedpouch"])
qq("quark:armor", "快速换甲", "一键换上一整套护甲。", "minecraft:iron_chestplate",
   [("check",)], [("xp", 20)], "circle", 1.5, -4.0, -9.0, ["quark:sort"])
write_chapter("quark", "quark:pickarang", 9, "夸克工坊", "把夸克用起来", Q)

# ---------------- existing chapters: double spacing + side quests ----------------
SIDE = {
    "guide": [
        ("guide:respawn", "设置重生点", "在床上睡一觉，设置重生点。", "minecraft:red_bed",
         [("check",)], [("xp", 20)], "circle", 1.5, -4.0, -6.0, ["248FCE53764A6893"]),
    ],
    "settlement": [
        ("settlement:furnace", "熔炉与箱子", "给基地配一个熔炉和箱子。", "minecraft:furnace",
         [("item", "minecraft:furnace", 1)], [("xp", 20)], "circle", 1.5, 4.0, -6.0, ["30519E41CB688427"]),
    ],
    "industry": [
        ("industry:belt", "传送带", "用传送带把机器串起来。", "create:belt_connector",
         [("item", "create:belt_connector", 4)], [("xp", 40)], "square", 2.0, 6.0, -3.0, ["61A03973C5E46EC0"]),
        ("industry:arm", "机械臂", "机械臂是自动化分拣的关键。", "create:mechanical_arm",
         [("item", "create:mechanical_arm", 1)], [("xp", 50)], "circle", 1.5, 6.0, -6.0, ["industry:belt"]),
    ],
    "army": [
        ("army:siege", "攻城工程师", "招募一名攻城工程师操作攻城器。", "hundred_years_war:scroll_siege_engineer",
         [("item", "hundred_years_war:scroll_siege_engineer", 1)], [("xp", 60)], "circle", 1.5, -4.0, -6.0, ["08AFB0416F248E9F"]),
        ("army:ten", "十人小队", "把队伍扩到 10 人。", "minecraft:iron_sword",
         [("check",)], [("xp", 80), ("item", "hundred_years_war:scroll_shieldman", 2)], "gear", 2.2, 4.0, -6.0, ["4E22D1438E8D160E"]),
    ],
    "expedition": [
        ("expedition:map", "地图与航点", "做一张地图并标记航点。", "minecraft:map",
         [("item", "minecraft:map", 1)], [("xp", 30)], "circle", 1.5, 0.0, -6.0, ["025E241A099E7638"]),
    ],
    "conquest": [
        ("conquest:defend", "守住第一块地", "在占领的区块建一个小据点。", "minecraft:cobblestone",
         [("check",)], [("xp", 60)], "circle", 1.5, 4.0, -6.0, ["0C3AA21DF37B84BD"]),
    ],
}

def append_side(fname, items):
    path = os.path.join(BASE, fname + ".snbt")
    t = open(path, encoding="utf-8").read()
    blocks = []
    for (name, title, desc, icon, tasks, rewards, shape, size, x, y, deps) in items:
        qid, block = quest_block(name, title, [desc], icon, tasks, rewards, shape, size, x, y, deps)
        blocks.append(block)
    idx = t.rfind("\n\t]\n}")
    assert idx > 0, fname
    t = t[:idx] + "\n" + "\n".join(blocks) + t[idx:]
    open(path, "w", encoding="utf-8").write(t)

def relayout():
    for f in os.listdir(BASE):
        if not f.endswith(".snbt"):
            continue
        path = os.path.join(BASE, f)
        t = open(path, encoding="utf-8").read()
        def mx(m):
            return "\t\t\tx: %.1fd" % (float(m.group(1)) * 2.0)
        def my(m):
            return "\t\t\ty: %.1fd" % (float(m.group(1)) * 2.0)
        t = re.sub(r"\t\t\tx: ([\d.\-]+)d", mx, t)
        t = re.sub(r"\t\t\ty: ([\d.\-]+)d", my, t)
        open(path, "w", encoding="utf-8").write(t)

# side quests first (their coords are already in doubled space)
for fname, items in SIDE.items():
    append_side(fname, items)
# then double existing coordinates (side quests also doubled -> need compensate)
relayout()
# side quests were written in doubled space; relayout doubled them again. Fix by halving side quest coords back.
for fname, items in SIDE.items():
    path = os.path.join(BASE, fname + ".snbt")
    t = open(path, encoding="utf-8").read()
    for (name, title, desc, icon, tasks, rewards, shape, size, x, y, deps) in items:
        qid = oid(name)
        # find block by id and set x/y to intended doubled-space values
        pat = re.compile(r'(id: "%s"[\s\S]*?)x: ([\d.\-]+)d\n(\t\t\ty: )([\d.\-]+)d' % qid)
        t = pat.sub(lambda m: m.group(1) + ("x: %.1fd\n" % x) + m.group(3) + ("%.1fd" % y), t, count=1)
    open(path, "w", encoding="utf-8").write(t)

print("farmer", len(F), "pets", len(P), "quark", len(Q), "side", sum(len(v) for v in SIDE.values()))
