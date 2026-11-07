# 工具盘点

逐项记录本地入口。输入和输出为静态线索，历史工具运行前须人工核对。对状态为「在用」的游戏入口，只从 workflow.py 调用。

| 入口 | 状态 | 输入和输出线索 | 游戏 | 验证 |
|---|---|---|---|---|
| `_five/analyze_dev_perf.py` | 在用 | 查看入口参数或调用者 | 可能，需核对 | 核对输入、输出和路径 |
| `_five/analyze_jfr_compact.py` | 在用 | 查看入口参数或调用者 | 可能，需核对 | 核对输入、输出和路径 |
| `_five/analyze_jfr_frames.py` | 在用 | 查看入口参数或调用者 | 可能，需核对 | 核对输入、输出和路径 |
| `_five/archive/_launch.ps1` | 历史参考 | 查看入口参数或调用者 | 可能，需核对 | 先隔离写入目标，再验证 |
| `_five/archive/_launch_menu.ps1` | 历史参考 | 查看入口参数或调用者 | 可能，需核对 | 先隔离写入目标，再验证 |
| `_five/create_flat_world.py` | 修后可用 | `nbt.save({'Data':D},str(old/'level.dat'))` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_five/dev_perf_suite.py` | 在用 | `ROOT=HERE/'perf'/'dev-20261104'`<br>`DEV=Path(r'C:\Users\Legen\Desktop\游戏\.minecraft\versions\梦想与远征_dev')`<br>`WORLD=DEV/'saves'/'perf_oldworld_20261103'` | 可能，需核对 | 通过统一入口预检 |
| `_five/dev_setup.py` | 历史参考 | `LIVE=Path(r'C:\Users\Legen\Desktop\游戏\.minecraft\versions\梦想与远征')`<br>`DEV=LIVE.parent/'梦想与远征_dev'`<br>`ROOT=HERE/'perf'/'dev-20261103'` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_five/download_candidates.py` | 修后可用 | `(P/'manifest.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_five/finish_dev_window.py` | 历史参考 | `config.write_text(after,encoding='utf-8')` | 未见启动调用 | 核对输入、输出和路径 |
| `_five/game_ui.ps1` | 修后可用 | 查看入口参数或调用者 | 未见启动调用 | 核对输入、输出和路径 |
| `_five/JfrCompact.java` | 在用 | 查看入口参数或调用者 | 未见启动调用 | 核对输入、输出和路径 |
| `_five/launch_dev_perf.py` | 在用 | `LIVE=Path(r'C:\Users\Legen\Desktop\游戏\.minecraft\versions\梦想与远征')`<br>`DEV=LIVE.parent/'梦想与远征_dev'`<br>`WORLD=Path(setup['dev_world'])` | 可能，需核对 | 通过统一入口预检 |
| `_five/launch_test.py` | 修后可用 | `(P/'test_process.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')` | 可能，需核对 | 先隔离写入目标，再验证 |
| `_five/patches/src/dsh/hywperf/mixin/HiddenChunkIndexMixin.java` | 修后可用 | 查看入口参数或调用者 | 未见启动调用 | 核对输入、输出和路径 |
| `_five/patches/src/dsh/seasonstweak/mixin/SeasonalCropGrowthHandlerMixin.java` | 修后可用 | 查看入口参数或调用者 | 未见启动调用 | 核对输入、输出和路径 |
| `_five/patches/src/dsh/windowicon/WindowIconMod.java` | 修后可用 | 查看入口参数或调用者 | 未见启动调用 | 核对输入、输出和路径 |
| `_five/perf_suite.py` | 修后可用 | `LIVE=Path(r'C:\Users\Legen\Desktop\游戏\.minecraft\versions\梦想与远征')`<br>`ROOT=HERE/'perf'/'ordinary-20261103'`<br>`BASE=ROOT/'baseline'` | 可能，需核对 | 先隔离写入目标，再验证 |
| `_five/refresh_dev_baseline.py` | 历史参考 | `ROOT=HERE/'perf'/'dev-20261104'` | 未见启动调用 | 核对输入、输出和路径 |
| `_five/seasons/evidence/ss_source/common/src/main/java/sereneseasons/config/FertilityConfig.java` | 修后可用 | 查看入口参数或调用者 | 未见启动调用 | 核对输入、输出和路径 |
| `_five/seasons/evidence/ss_source/common/src/main/java/sereneseasons/init/ModFertility.java` | 修后可用 | 查看入口参数或调用者 | 未见启动调用 | 核对输入、输出和路径 |
| `_five/seasons/evidence/ss_source/common/src/main/java/sereneseasons/mixin/client/MixinBiomeClient.java` | 修后可用 | 查看入口参数或调用者 | 未见启动调用 | 核对输入、输出和路径 |
| `_five/seasons/evidence/ss_source/common/src/main/java/sereneseasons/mixin/client/MixinLevelRenderer.java` | 修后可用 | 查看入口参数或调用者 | 未见启动调用 | 核对输入、输出和路径 |
| `_five/seasons/evidence/ss_source/common/src/main/java/sereneseasons/mixin/MixinBiome.java` | 修后可用 | 查看入口参数或调用者 | 未见启动调用 | 核对输入、输出和路径 |
| `_five/seasons/evidence/ss_source/common/src/main/java/sereneseasons/mixin/MixinBlockStateBase.java` | 修后可用 | 查看入口参数或调用者 | 未见启动调用 | 核对输入、输出和路径 |
| `_five/seasons/evidence/ss_source/common/src/main/java/sereneseasons/mixin/MixinLevel.java` | 修后可用 | 查看入口参数或调用者 | 未见启动调用 | 核对输入、输出和路径 |
| `_five/seasons/evidence/ss_source/common/src/main/java/sereneseasons/mixin/MixinServerLevel.java` | 修后可用 | 查看入口参数或调用者 | 未见启动调用 | 核对输入、输出和路径 |
| `_five/seasons/evidence/ss_source/common/src/main/java/sereneseasons/season/SeasonalCropGrowthHandler.java` | 修后可用 | 查看入口参数或调用者 | 未见启动调用 | 核对输入、输出和路径 |
| `_five/seasons/finish_audit.py` | 修后可用 | `(R/'growth_entry_evidence.json').write_text(json.dumps(entry,indent=2),encoding='utf-8')`<br>`(R/'crop_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')`<br>`(R/'growth_exceptions.json').write_text(json.dumps(exceptions,ensure_ascii=False,indent=2),encoding=` | 未见启动调用 | 核对输入、输出和路径 |
| `_five/seasons/generate.py` | 修后可用 | `out.write_text(json.dumps({'replace':False,'values':sorted(tagadd[kind,season])},ensure_ascii=False,`<br>`out.write_text(json.dumps({'replace':False,'values':['farm_and_charm:onion_crop']},indent=2)+'\n',en`<br>`(R/'crop_stage_audit.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='u` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_five/seasons/inspect.py` | 修后可用 | `ROOT=pathlib.Path(__file__).parent`<br>`(out/(cl+'.txt')).write_text(r.stdout+r.stderr,encoding='utf-8')`<br>`(E/'inventory.json').write_text(json.dumps(inv,indent=2),encoding='utf-8')` | 可能，需核对 | 先隔离写入目标，再验证 |
| `_five/seasons/inspect_extra.py` | 修后可用 | `r=subprocess.run(['javap','-classpath',str(p),'-p','-c',cl],capture_output=True,text=True,encoding='` | 可能，需核对 | 核对输入、输出和路径 |
| `_five/seasons/inspect_foundation_vanilla.py` | 修后可用 | `cl=n[:-6].replace('/','.');r=subprocess.run(['javap','-classpath',str(cp),'-p','-c',cl],capture_outp`<br>`cl='net.minecraft.world.level.block.'+short;r=subprocess.run(['javap','-classpath',str(p),'-p','-c',`<br>`assets={n:json.loads(z.read(n)) for n in z.namelist() if '/blockstates/' in n and n.endswith('.json'` | 可能，需核对 | 核对输入、输出和路径 |
| `_five/seasons/inspect_more.py` | 修后可用 | `r=subprocess.run(['javap','-classpath',str(p),'-p','-c',cl],capture_output=True,text=True,encoding='`<br>`assets={n:json.loads(z.read(n)) for n in z.namelist() if '/blockstates/' in n and n.endswith('.json'` | 可能，需核对 | 核对输入、输出和路径 |
| `_five/setup_isolation.py` | 修后可用 | `(B/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')`<br>`f.write_text(text,encoding='utf-8')` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_five/vehicles/inspect_cbc_resources.py` | 修后可用 | `ROOT = Path(r'C:\Users\Legen\Desktop\游戏\.minecraft\versions\梦想与远征\mods')`<br>`OUT = Path(__file__).resolve().parent / 'evidence_cbc_resources.json'`<br>`OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_five/verify_window_icon.py` | 修后可用 | `im.save('_five/icons/verified-window-icon.png')`<br>`ImageGrab.grab().save('_five/icons/verified-taskbar-screen.png')` | 未见启动调用 | 核对输入、输出和路径 |
| `_five/watch_test.py` | 修后可用 | 查看入口参数或调用者 | 可能，需核对 | 核对输入、输出和路径 |
| `_pack_build/check_emblem.py` | 修后可用 | 查看入口参数或调用者 | 未见启动调用 | 核对输入、输出和路径 |
| `_pack_build/make_emblem_icon.py` | 修后可用 | `icon256.save(r"C:\Users\Legen\Desktop\游戏\.minecraft\versions\梦想与远征\PCL\Logo.png", "PNG")`<br>`icon256.save(r"C:\Users\Legen\Desktop\梦想与远征\_pack_build\_uipack\pack.png", "PNG")`<br>`icon512.save(r"C:\Users\Legen\Desktop\梦想与远征\_pack_build\emblem_512.png", "PNG")` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_pack_build/make_emblem_icon2.py` | 修后可用 | `make(256, 236).save(r"C:\Users\Legen\Desktop\游戏\.minecraft\versions\梦想与远征\PCL\Logo.png", "PNG")`<br>`make(256, 236).save(r"C:\Users\Legen\Desktop\梦想与远征\_pack_build\_uipack\pack.png", "PNG")`<br>`make(512, 472).save(r"C:\Users\Legen\Desktop\梦想与远征\_pack_build\emblem_512.png", "PNG")` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_pack_build/make_icons.py` | 修后可用 | `im.save(p)` | 未见启动调用 | 核对输入、输出和路径 |
| `_pack_build/make_logo.py` | 修后可用 | `img.save(out, "PNG")` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_pack_build/make_mce_icon.py` | 修后可用 | `src.resize((64, 64), Image.LANCZOS).save(os.path.join(folder, "icon.png"), "PNG")`<br>`src.resize((128, 128), Image.LANCZOS).save(os.path.join(folder, "icon_128.png"), "PNG")` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_pack_build/make_pcl_logo.py` | 修后可用 | `img.resize((256, 256), Image.LANCZOS).save(out, "PNG")` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_pack_build/make_uipack.py` | 修后可用 | `OUT = r"C:\Users\Legen\Desktop\梦想与远征\_pack_build\_uipack"`<br>`import shutil; shutil.rmtree(OUT)`<br>`logo.save(os.path.join(ASSETS, "textures", "gui", "title", "minecraft.png"))` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_pack_build/verify_icons.py` | 修后可用 | 查看入口参数或调用者 | 未见启动调用 | 先隔离写入目标，再验证 |
| `_pack_build/write_readme.py` | 修后可用 | 查看入口参数或调用者 | 未见启动调用 | 先隔离写入目标，再验证 |
| `_pack_build/zip_uipack.py` | 修后可用 | 查看入口参数或调用者 | 未见启动调用 | 先隔离写入目标，再验证 |
| `_recruits/build_cp.py` | 历史参考 | 查看入口参数或调用者 | 未见启动调用 | 先隔离写入目标，再验证 |
| `_recruits/package.py` | 历史参考 | `ROOT = r"C:\Users\Legen\Desktop\梦想与远征\_recruits"`<br>`OUT_DIR = os.path.join(ROOT, "out")` | 未见启动调用 | 核对输入、输出和路径 |
| `_recruits/scan_entities.py` | 历史参考 | 查看入口参数或调用者 | 未见启动调用 | 先隔离写入目标，再验证 |
| `_recruits/stubs/org/jetbrains/annotations/NotNull.java` | 历史参考 | 查看入口参数或调用者 | 未见启动调用 | 核对输入、输出和路径 |
| `_recruits/stubs/org/jetbrains/annotations/Nullable.java` | 历史参考 | 查看入口参数或调用者 | 未见启动调用 | 核对输入、输出和路径 |
| `_recruits/tools/AtApply.java` | 历史参考 | 查看入口参数或调用者 | 未见启动调用 | 核对输入、输出和路径 |
| `_struct/_fids.py` | 修后可用 | 查看入口参数或调用者 | 未见启动调用 | 核对输入、输出和路径 |
| `_struct/add_place_functions.py` | 修后可用 | `BASE = os.path.dirname(os.path.abspath(__file__))`<br>`OUT = os.path.join(BASE, "out")` | 未见启动调用 | 核对输入、输出和路径 |
| `_struct/build_datapack.py` | 修后可用 | `BASE = os.path.dirname(os.path.abspath(__file__))`<br>`NBT_DIR = os.path.join(BASE, "out", "nbt")`<br>`BUILD_DIR = os.path.join(BASE, "out", "datapack")` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_struct/build_factions.py` | 修后可用 | `BASE = os.path.dirname(os.path.abspath(__file__))`<br>`OUT = os.path.join(BASE, "out")`<br>`NBT_DIR = os.path.join(OUT, "nbt_factions")` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_struct/build_factory.py` | 修后可用 | `BASE = os.path.dirname(os.path.abspath(__file__))`<br>`OUT = os.path.join(BASE, "out", "nbt", "steam_factory.nbt")`<br>`size = v.save(OUT)` | 未见启动调用 | 核对输入、输出和路径 |
| `_struct/build_factory_jar.py` | 修后可用 | `BASE = os.path.dirname(os.path.abspath(__file__))`<br>`OUT = os.path.join(MODS, "dream_expedition_steam_factory.jar")` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_struct/build_factory_probe.py` | 修后可用 | `BASE = os.path.dirname(os.path.abspath(__file__))`<br>`OUT = os.path.join(MODS, "zfactory.jar")` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_struct/build_industrial5.py` | 修后可用 | `BASE = os.path.dirname(os.path.abspath(__file__))`<br>`NBT_DIR = os.path.join(BASE, "out", "nbt")`<br>`PREVIEW_DIR = os.path.join(BASE, "out", "preview")` | 未见启动调用 | 核对输入、输出和路径 |
| `_struct/build_industrial5_jar.py` | 修后可用 | `BASE = os.path.dirname(os.path.abspath(__file__))`<br>`OUT = os.path.join(MODS, "dream_expedition_industrial5.jar")` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_struct/build_industrial_v2.py` | 修后可用 | `BASE = os.path.dirname(os.path.abspath(__file__))`<br>`NBT_DIR = os.path.join(BASE, "out", "nbt")`<br>`PREVIEW_DIR = os.path.join(BASE, "out", "preview")` | 未见启动调用 | 核对输入、输出和路径 |
| `_struct/build_industrial_v2_jar.py` | 修后可用 | `BASE = os.path.dirname(os.path.abspath(__file__))`<br>`OUT = os.path.join(MODS, "dream_expedition_industrial7.jar")` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_struct/build_industrial_v3.py` | 修后可用 | `BASE = os.path.dirname(os.path.abspath(__file__))`<br>`NBT_DIR = os.path.join(BASE, "out", "nbt")`<br>`PREVIEW_DIR = os.path.join(BASE, "out", "preview")` | 未见启动调用 | 核对输入、输出和路径 |
| `_struct/build_industrial_v4.py` | 修后可用 | `BASE = os.path.dirname(os.path.abspath(__file__))`<br>`NBT_DIR = os.path.join(BASE, "out", "nbt")`<br>`PREVIEW_DIR = os.path.join(BASE, "out", "preview")` | 未见启动调用 | 核对输入、输出和路径 |
| `_struct/build_industrial_v4_jar.py` | 修后可用 | `BASE = os.path.dirname(os.path.abspath(__file__))`<br>`OUT = r"C:\Users\Legen\Desktop\游戏\.minecraft\versions\梦想与远征\mods\dream_expedition_industrial7.jar"` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_struct/capture_game.ps1` | 修后可用 | 查看入口参数或调用者 | 未见启动调用 | 核对输入、输出和路径 |
| `_struct/designs.py` | 修后可用 | `OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")`<br>`NBT_DIR = os.path.join(OUT_DIR, "nbt")`<br>`IMG_DIR = os.path.join(OUT_DIR, "preview")` | 未见启动调用 | 核对输入、输出和路径 |
| `_struct/faction_designs.py` | 修后可用 | `OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")`<br>`NBT_DIR = os.path.join(OUT_DIR, "nbt_factions")`<br>`IMG_DIR = os.path.join(OUT_DIR, "preview_factions")` | 未见启动调用 | 核对输入、输出和路径 |
| `_struct/inspect_ltab.py` | 修后可用 | `BASE = os.path.dirname(os.path.abspath(__file__))`<br>`OUT = os.path.join(BASE, "out", "ltab")` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_struct/make_datapack_mod.py` | 修后可用 | `BASE = os.path.dirname(os.path.abspath(__file__))`<br>`OUT = os.path.join(BASE, "out", "dream_expedition_landmarks.jar")`<br>`MODS_DIR = r"C:\Users\Legen\Desktop\游戏\.minecraft\versions\梦想与远征\mods"` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_struct/make_menu_music.py` | 修后可用 | `OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "music")` | 未见启动调用 | 核对输入、输出和路径 |
| `_struct/nbt.py` | 在用 | `def save(root_mapping, path):` | 未见启动调用 | 核对输入、输出和路径 |
| `_struct/nbt_read.py` | 在用 | 查看入口参数或调用者 | 未见启动调用 | 核对输入、输出和路径 |
| `_struct/nbt_typed.py` | 在用 | 查看入口参数或调用者 | 未见启动调用 | 核对输入、输出和路径 |
| `_struct/registry.py` | 修后可用 | `MODS_DIR = r"C:\Users\Legen\Desktop\游戏\.minecraft\versions\梦想与远征\mods"`<br>`OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "registry.json")` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_struct/scan_garrison.py` | 修后可用 | 查看入口参数或调用者 | 未见启动调用 | 先隔离写入目标，再验证 |
| `_struct/study_exemplars.py` | 修后可用 | `BASE = os.path.dirname(os.path.abspath(__file__))`<br>`OUT = os.path.join(BASE, "out", "study")` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_struct/voxel.py` | 修后可用 | `BASE = os.path.dirname(os.path.abspath(__file__))`<br>`REGISTRY_PATH = os.path.join(BASE, "registry.json")`<br>`COLORS_PATH = os.path.join(BASE, "block_colors.json")` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_tools/add_industry_quests.py` | 修后可用 | `ROOT = "50E55847CE86D110"   # 安山合金量产` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_tools/apply_auto_tasks.py` | 修后可用 | `BASE = r"C:\Users\Legen\Desktop\游戏\.minecraft\versions\梦想与远征\config\ftbquests\quests\chapters"` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_tools/apply_auto_tasks_v2.py` | 修后可用 | `BASE = r"C:\Users\Legen\Desktop\游戏\.minecraft\versions\梦想与远征\config\ftbquests\quests\chapters"` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_tools/clean_save_meta.py` | 修后可用 | `root.save()`<br>`root.save()`<br>`shutil.rmtree(p)` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_tools/clean_save_regions.py` | 修后可用 | 查看入口参数或调用者 | 未见启动调用 | 先隔离写入目标，再验证 |
| `_tools/fast_scan_save_ns.py` | 修后可用 | `OUT = sys.argv[2]` | 未见启动调用 | 核对输入、输出和路径 |
| `_tools/fix_last_old_refs.py` | 修后可用 | 查看入口参数或调用者 | 未见启动调用 | 先隔离写入目标，再验证 |
| `_tools/gen_create_world_music.py` | 修后可用 | `OUT = r"C:\Users\Legen\Desktop\梦想与远征\_tools\music_out"` | 未见启动调用 | 核对输入、输出和路径 |
| `_tools/gen_quest_art.py` | 修后可用 | `BANNER_DIR = os.path.join(ASSETS, "dream_expedition", "textures", "quest_art", "banners")`<br>`GUI_DIR = os.path.join(ASSETS, "ftbquests", "textures", "gui")`<br>`im.save(os.path.join(BANNER_DIR, fname))` | 未见启动调用 | 先隔离写入目标，再验证 |
| `_tools/gen_quests.py` | 在用 | `BASE = legacy_quest_chapters(parser.parse_args().chapters)` | 未见启动调用 | 核对输入、输出和路径 |
| `_tools/patch_hyw_recruit_cost.py` | 修后可用 | 查看入口参数或调用者 | 未见启动调用 | 先隔离写入目标，再验证 |
| `_tools/patch_hyw_recruit_cost_v2.py` | 修后可用 | 查看入口参数或调用者 | 未见启动调用 | 先隔离写入目标，再验证 |
| `_tools/PatchHywEnchant.java` | 修后可用 | 查看入口参数或调用者 | 未见启动调用 | 核对输入、输出和路径 |
| `_tools/relayout_quests.py` | 在用 | `BASE = legacy_quest_chapters(parser.parse_args().chapters)` | 未见启动调用 | 核对输入、输出和路径 |
| `restore_settings.ps1` | 历史参考 | 查看入口参数或调用者 | 未见启动调用 | 先隔离写入目标，再验证 |

Recruits 内嵌上游源码树作为一个历史输入保留。源码树逐文件不纳入自有工具清单。
