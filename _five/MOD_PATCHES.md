# Mod 内部改动登记表（唯一权威）

> **规则（从 2026-11-03 起生效）**
> 1. 任何对 mod 内部行为的改动（Mixin / 字节码补丁 / KubeJS 覆写 mod 行为）都必须登记在本文件，**没登记等于没改**。
> 2. 每次下载或更新任何 mod 后，必须先逐条读本文件，按「更新后如何重做」一节重新实现，并重跑「验证」一节，通过后才允许放进游戏。
> 3. 每条记录必须包含：ID、目标 mod 与**精确版本**、注入点、实际代码、目的、验证方法与**实测数据**、更新后的重做步骤、临时停用方式、已知失败模式。
> 4. 目标 mod 版本变化后，本文件里的旧记录**不会自动失效**；必须逐条重新确认，并更新「已验证版本」字段。

---

## P18 · 独立本地 develop 快照入口（2026-11-07，实施前登记）

- 目标：AutoModpack 4.0.7，基于 P15/P17 构建器及当前已验证客户端。Preload.updateAll 在确认 selectedModpackDir 后，若存在 `.dsh-local-profile` 标记，调用只读本地加载并直接返回，不查询远端、更新、复制或清理。
- ModpackUpdater.loadInstalledModpack 增加 Path 静态重载，保留实例入口及 P17 的启用 JAR 去重规则。本地目录仍位于 dev/automodpack/modpacks 内，标记由本轮工具生成；配置 updateSelectedModpackOnLaunch 保持 false。
- 重建：tools/automodpack_bridge.py 使用原有锁定上游哈希、Java 21 目标、精确锚点，源码随 LGPL 制品附带。不得将该本地快照上传为云端发布。
- 验证：构建逐成员比对、实际加载方法隔离测试、静态检查本地分支早于网络请求并直接返回；本轮不启动游戏，PCL 加载和服装渲染均待验。
- 回滚：退出 dev 后恢复本轮备份的更新器和客户端配置，原云服受管快照不变；开发快照保留归档，不迁移世界。

## P19 · 首批食品附属标签适配（2026-11-07，实施前登记）

- 目标：Veggies Delight 1.9.3、Crabber's Delight 1.3.1、Ender's Delight 1.3.1；FD 1.3.4、Create 6.0.10、现有 Let’s Do。仅以数据标签和必要的精确配方覆盖连接同义原料，保留注册 ID、原生厨锅/砧板及特色料理。
- 先盘点 JAR 原始数据和条件加载，只有确认缺口才新增；不添加双向兑换，不转换玩家库存。确切改动、输入哈希、验证和回滚在本轮开发报告登记。
- 重建/回滚：工具生成 pack 中自有数据并安装 dev；撤销本轮新增数据、恢复配置与原开发快照选择。离线检查不等同服务端加载或实际出料验收。

## P04 · HYW 火枪耐久系统

- **状态**：已实现、隔离实测通过、已安装主实例
- **目标 mod**：Hundred Years War `0.7.1r-fix1`（`HundredYearsWar-0.7.1r-fix1-1.21.1-neoforge.jar`）
- **文件**：`kubejs/server_scripts/95_hyw_gun_enchant.js`
- **背景**：`HandgonneItem` / `MatchlockItem` 直接继承 `Item`，`use()` 只做「查冷却→扣弹药→生成 BulletEntity→上冷却」，
  **没有任何耐久逻辑**（源码与字节码均确认无 `hurtAndBreak`）。
- **做法**（纯 KJS，不改 HYW 代码）：
  1. 每 20 tick 扫描玩家背包，对 `handgonne`/`matchlock` 且没有 `max_damage` 组件的物品栈执行
     `stack.set(DataComponents.MAX_DAMAGE, 250/350)`；
  2. 监听 `EntityEvents.spawned('hundred_years_war:bullet')`，仅当子弹拥有者是玩家且主手是对应火枪时，
     扣 1 点耐久；创造模式跳过；按耐久等级做 `1/(等级+1)` 概率免扣；
  3. 耐久达到上限时移除该物品并播放 `minecraft:item.break`。
- **实测（隔离实例 `20261103-110924`）**：连开 5 枪耐久 0→1→2→3→4→5（上限 250）；创造模式开 2 枪不变；
  把耐久设为 249/250 再开一枪 → 主手变为空气。
- **更新后如何重做**：
  1. 确认物品 id 与子弹实体 id 未变（`hundred_years_war:handgonne` / `matchlock` / `bullet`）；
  2. 若 HYW 自己加了耐久（`Item.Properties.durability`），删除本补丁的 max_damage 段，避免双重耐久；
  3. 重跑「五枪 + 创造 + 归零」三组验证。
- **临时停用**：删除该脚本。
- **已知失败模式**：若 HYW 改了子弹实体 id，脚本静默不扣耐久（日志无 `[HYW_PATCH] shot`）。

## P05 · HYW 火枪多重射击

- **状态**：已实现、隔离实测通过、已安装主实例（与 P04 同一脚本）
- **原理**：弩的多重射击是「一次装填 3 发、只耗 1 弹药、左右各偏约 10°」。
  在子弹生成事件里，对带多重射击的玩家额外 `new BulletEntity(...)` 生成 2 颗，
  复制原子弹的伤害/穿透，速度向量绕 Y 轴 ±10° 旋转，并打标签 `dsh_multishot_extra` 防止递归。
- **实测**：多重射击 III 开一枪，场上子弹数 +3（1 原始 + 2 额外），弹药只消耗 1。
- **更新注意**：`BulletEntity` 构造签名 `(EntityType, LivingEntity, Level)` 必须仍存在。
- **停用**：删除脚本；火枪保留单发。

## P06 · HYW 火枪穿透

- **状态**：已实现、隔离实测通过、已安装主实例（与 P04 同一脚本）
- **原理**：`BulletEntity extends AbstractArrow`，其 `onHit` 先调 `super.onHit()`，只在
  `getPierceLevel()==0` 时 `discard()`。1.21.1 的 `AbstractArrow#setPierceLevel(byte)` 是 **private**，
  所以用存档数据：`saveWithoutId(tag)` → `tag.putByte("PierceLevel", n)` → `load(tag)`，
  随后恢复位置与速度（`load` 可能改动它们）。
- **实测**：穿透 III 一发命中并穿过两只铁傀儡（两只都掉 15 血）。
- **更新后如何重做**：确认 `AbstractArrow` 仍用 `PierceLevel` 这个 NBT 键；
  若 1.21.x 后续把 setter 公开，可直接改用 setter 并删掉 NBT 手法。
- **已知失败模式**：若 NBT 键改名，穿透静默失效（子弹仍然单目标）。

---

## P03 · 季节反季生长速度 1/6 → 1/2

- **状态**：已实现、隔离 A/B 通过、已安装到主实例
- **目标 mod**：Serene Seasons `10.1.0.9`（NeoForge 1.21.1）
- **已验证版本**：`SereneSeasons-neoforge-1.21.1-10.1.0.9.jar`
- **注入点**：`sereneseasons.season.SeasonalCropGrowthHandler#onCropGrowth`
- **原理**：SS 在反季且无温室时用 `random.nextInt(6) == 0` 决定是否放行（约 1/6 速度）。
  把该方法里的常量 `6` 改成 `2`，即 `nextInt(2) == 0` → **50% 放行**。
- **代码**：`_five/patches/src/dsh/seasonstweak/mixin/SeasonalCropGrowthHandlerMixin.java`
  ```java
  @Mixin(targets = "sereneseasons.season.SeasonalCropGrowthHandler")
  public class SeasonalCropGrowthHandlerMixin {
      @ModifyConstant(method = "onCropGrowth", constant = @Constant(intValue = 6), require = 0)
      private static int dsh$halfChance(int original) { return 2; }
  }
  ```
- **产物**：`_five/patches/dsh_seasons_tweak-1.0.0.jar`（2,006 字节），modId `dsh_seasons_tweak`，
  只含 `[[mixins]]`，无入口类。
- **构建方法（不依赖 Gradle / 不联网）**：
  1. `javac --release 21 -cp <libraries>/org/spongepowered/mixin/0.8.7/mixin-0.8.7.jar`
     编译 `_five/patches/src` 下的源码到 `build/classes`；
  2. 把 `build/classes/dsh` + `dsh_seasons_tweak.mixins.json` + `META-INF/neoforge.mods.toml` 打包成 jar。
- **验证（隔离实例 five_flat，SPRING，大麦为反季作物）**：
  - 场景：32 格 `farm_and_charm:barley_crop[age=0]`，`randomTickSpeed=60`（测试加速），1200 tick；
  - **未打补丁**：总 age 增量 **7**（`_five/runs/20261103-103654`）；
  - **打补丁**：总 age 增量 **32**（`_five/runs/20261103-103900`）；
  - 32 格全部存活，无枯死 → 与行为值 0（缓慢生长）一致。
  - 局限：增量样本较小（7/32），只证明"显著变快"，未做 200 次单刻通过率统计；若需严格 50% 需更大样本。
- **更新后如何重做**：
  1. 解压新 SS jar，`javap -p -c sereneseasons.season.SeasonalCropGrowthHandler` 确认
     `onCropGrowth` 里仍是 `nextInt(6)`；
  2. 若常量仍是 6：直接复用现有补丁 jar，重跑验证；
  3. 若常量变了（例如 8 或改成别的方式）：把 `@Constant(intValue = 6)` 改成新常量，
     或改用 `@Redirect` 重定向 `RandomSource.nextInt(I)`；重新编译、重测；
  4. 更新本记录的「已验证版本」与验证数据。
- **临时停用**：删除 `mods/dsh_seasons_tweak-1.0.0.jar`，SS 自动回到 1/6。
- **已知失败模式**：`require = 0` → SS 改了方法时补丁**静默失效**（游戏不崩，但速度回到 1/6）。
  因此**每次更新 SS 必须重跑验证**，不能只看游戏能启动。

---

## P02 · HYW 火枪「快速装填」生效

- **状态**：已启用（KubeJS，非 mixin）
- **目标 mod**：Hundred Years War `0.7.1r-fix1`（`HundredYearsWar-0.7.1r-fix1-1.21.1-neoforge.jar`）
- **文件**：`kubejs/server_scripts/73_hyw_quick_charge.js`
- **原理**：HYW 火枪本体不读取 `quick_charge` 附魔；脚本在玩家主手为
  `hundred_years_war:handgonne`（基础 100 tick）或 `matchlock`（120 tick）且带有快速装填时，
  把物品冷却改为 `base × (1 - 0.2 × 等级)`。
- **验证**：主手火枪 + 快速装填 I/II/III，开火后冷却分别约为 80/60/40 tick（手铳）。
- **更新后如何重做**：确认 HYW 物品 id 与基础冷却未变；若 HYW 自己开始读 quick_charge，删掉本脚本。
- **临时停用**：把文件改名为 `.off`。
- **已知失败模式**：若 HYW 改了物品 id 或冷却机制，脚本静默不生效（无报错）。

---

## P01 · 土豆炮附魔修复（第三方，不是我们写的）

- **状态**：已安装
- **mod**：`createpotatocannonenchantfix-1.0.0.jar`（第三方，Modrinth 校验）
- **作用**：Create 6.0.10 的 `PotatoProjectileEntity.setEnchantmentEffectsFromCannon` 只读
  `POTAO_RECOVERY`，本 mod 用 mixin 补上 Power/Punch/Flame 的效果。
- **验证**：力量 0/I/V 真实碰撞伤害 5/5/5 → 5/6/10；生存手持实测扣血 10、弹药 64→63、耐久 +1。
- **升级注意**：Create 若修复了该 bug，本 mod 可能重复加成 → 升级 Create 后必须重跑上面的伤害 A/B。

---

## 已退役 / 已移除

| 项 | 原用途 | 现状 |
|---|---|---|
| `kubejs/client_scripts/91_all_enchantments_jei.js` | 自己生成 140 本附魔书给 JEI | 已移除，改用现成 `Universal Enchantment Info`；备份 `_five/backup/91_all_enchantments_jei.js` |
| `_five/seasons/` 下 111 条作物标签 | 手写季节标签 | 已弃用，改用现成 `Seasonal Let's Do` 自带标签 |

## P07 HYW HiddenChunkIndex 缓存（拒绝晋升，仅历史记录）

- **状态**：实验无收益，未安装普通版；禁止复用现有实现。
- **源码/产物**：`_five/patches/src/dsh/hywperf/mixin/HiddenChunkIndexMixin.java`、`_five/patches/dsh_hyw_perf-1.0.0.jar`。
- **行为**：重定向 `contains` 内 Map.get，缓存上一次维度键与集合。
- **拒绝原因**：静态缓存可能跨实例污染；集合替换/移除时无失效机制，可能读到陈旧数据。旧采样无可证实收益。
- **更新后处理**：不自动重装；若未来确有热点，须先设计覆盖替换/移除/生命周期的正确缓存失效，再独立测量。
- **回滚**：无正式实例改动可回滚，保留禁用状态。

## P08 dsh_window_icon — 游戏窗口/任务栏图标

- **目的**：把 Minecraft 窗口（任务栏）图标换成小鸡图，纯客户端外观。
- **原理**：`Minecraft` 的窗口图标来自 `vanillaPackResources`（客户端 jar 内 `assets/minecraft/icons/`），
  资源包无法覆盖；本补丁在第一个客户端 tick 用 LWJGL `GLFW.glfwSetWindowIcon` 直接设置窗口图标。
- **源码**：`_five/patches/src/dsh/windowicon/WindowIconMod.java`
- **产物**：`_five/patches/dsh_window_icon-1.0.0.jar`，modId `dsh_window_icon`，
  `displayTest="IGNORE_ALL_VERSION"`，`side=CLIENT`，不影响联机校验。
- **图标文件**：`config/dsh_window_icon.png`（实例根目录下），缺失时保持原版图标。
- **依赖**：只依赖 neoforge + lwjgl-glfw（游戏自带），无第三方库。
- **重新编译**（mod 升级后）：
  1. 确认 `libraries/net/neoforged/fancymodloader/loader/<ver>`、`bus`、`mergetool-api`、
     `neoforge-<ver>-universal.jar`、`lwjgl-glfw-3.3.3.jar`、`lwjgl-3.3.3.jar` 存在；
  2. `javac -encoding UTF-8 --release 21 -cp "<上述 jars 分号连接>" -d build/windowicon src\...\WindowIconMod.java`
  3. 按 `build/windowicon_stage` 结构打 jar（`META-INF/neoforge.mods.toml` + `dsh/`）。
- **2026-11-03 修复**：旧实现按进程工作目录查找配置，PCL 启动时可能找错目录；改为 `FMLPaths.CONFIGDIR`。旧实现把全部尺寸像素（约 350 KB）放在默认约 64 KB 的 LWJGL MemoryStack，可能抛出栈容量异常并被静默吞掉；改为 `MemoryUtil.memAlloc/memFree`，仅 GLFWImage 结构保留在栈。异常现在输出完整堆栈，不再静默。
- **验证**：必须在 Windows 实际窗口读取 WM_GETICON 并导出图像，核验小鸡图标；只有启动无报错不足以证明生效。隔离启动 `20261103-203244` 已从实际 Windows 窗口 HWND=2885968 读取 WM_GETICON 并导出 `_five/icons/verified-window-icon.png`，目视确认是小鸡；桌面截图中任务栏游戏按钮也已显示小鸡。未进入任何世界。修复后 jar SHA256=`2f9bbd6db03591e4460207207552b4e2ea9008aadbbb9abb49a3dff7e3889a8c`，正式与 dev 均已同步。
- **回滚**：删除 `mods/dsh_window_icon-1.0.0.jar`。

## 2026-11-04 性能开发状态（非新增正式内部补丁）

- 本轮没有新增Mixin/字节码优化补丁，也未修改共享Java、NeoForge或Flywheel库。P07仍禁止复用，P08未更改。
- 仅在dev切换irisflw及官方配置：Spark后台采样、Flywheel workerThreads；这些是候选试验，**不是已选定正式配置**，不自动重装或晋升。
- [帧采样脚本](<_five/perf/100_perf_measure.js>)与[路线脚本](<_five/perf/100_perf_route.js>)仅临时安装于dev；路线只允许专用测试地图副本，测试后清理。发布必须排除它们，不迁移实验存档。
- [锁等待证据与配置审计](<_five/perf/irisflw-thread-lock-audit.md>)、[单次试验记录与限制](<_five/perf/dev-20261104/round1.md>)持续登记。重复收益、图形/机械正确性未完成前，不作为正式优化结论。
- 离线JFR读取工具不是游戏mod，不安装到任何游戏实例；调整采样器/分析器不等于给游戏实施了性能补丁。

## P09 · Vinery 连锁棚架掉落归集（dev 候选）

- 目标：Vinery 1.5.6、FTB Ultimine 2101.1.14、KubeJS 2101.7.2-build.377。
- 注入点：已有 CropLikeHandler 的 StemBlock 分支。将原来直接生成实体的 dropGrapes 改为 collector.add。成熟株使用 GRAPE 果实和原公式 3 + nextInt(2)，保留采后 age=2 和采摘音效。普通右键仍由 Vinery 处理。
- 重建：从 pack/kubejs/startup_scripts/81_vinery_ultimine.js 安装到 dev 同路径并重启。更新时用 javap 核对 StemBlock.dropGrapes、GRAPE、AGE、CropHarvesting 的 collector 及现有兼容分支。
- 验证：检查所有收获分支通过 collector；dev 对成熟棚架做连锁和普通右键对照。已验证的原字节码公式为成熟时 3–4 枚；dev 启动、直接注册和事件注册通过。实际采摘落点待验。
- 回滚：恢复本次 dev 文件备份并重启。接口签名变化可能导致脚本注册或收获失败，查看 vinery-ultimine 日志。

## P10 · Let’s Do 配方统一与 Create 黄油（dev 候选）

- 目标：Farm & Charm 1.1.29、Bakery 2.1.11、Farmer’s Delight 1.3.4、Let’s Do Compat 2.3.1、Create 6.0.10。
- 扩展现有 KubeJS 映射，将生培根、培根煎蛋、烤培根三明治统一为 FD。保留原注册，明确删除旧产出配方，并同步 JEI、创造栏、关键标签与现有成就引用。另移除自动生成的 letsdocompat:create/crafting_bowl/butter，使用与 Create 巧克力相同的 c:milk 流体标签格式，1 桶液态奶产 4 黄油。同样覆盖自动生成的 cake_dough 和 oatmeal_with_strawberries，保留其余原料和产量。
- 重建：复制本次 pack/kubejs 对应源码到 dev。升级后重新枚举旧物品配方和引用、检查自动生成 ID、Create 流体 codec 和现有 tag。
- 验证：脚本语法、输入输出映射、JSON 和来源字节码离线核对。dev 服务端已核验新旧配方 ID。管道进奶、实际出料以及旧物品转换待验。
- 回滚：恢复本次 dev 文件备份，移除本轮新增文件后重启。测试过程中已经转换的库存通过恢复测试快照回滚。

## P11 · Vinery 发酵桶同批酒日期对齐（开发）

- 目标 Vinery 1.5.6，原版 SHA-256 7e5e4e901a599a499bd510490ec12e72e8547e53b61790778fa7848852c451ec。
- 注入 FermentationBarrelBlockEntity.canCraft 的 fits 调用及 craft 的 ItemStack.grow 调用。前者仅对旧成品副本对齐 WINE_YEAR 的 brewedDay，再由原 fits 检查同款、其他组件与容量。后者仅在合批成功时更新实际旧酒的 brewedDay。没有 WINE_YEAR 的产品继续使用原比较。
- 重建：执行 tools/gameplay_next.py wine（JDK 24 和现有 ASM 9.8），从校验过的原版 JAR 生成 dev 候选。构建拒绝签名 JAR、错误哈希或不唯一的调用点。
- 验证：核对生成字节码及服务端加载。跨日同款已在 dev 测得 1 瓶第 1 日合为 2 瓶第 3206 日。候选 SHA-256 8a4cbcf80fd2089545c769bb1b665dcdd17a56c285cc0bb66b9881a3b53df327。异款、满槽及漏斗尚待场景回归。回滚：关闭 dev 后恢复 .stage/gameplay-next/backup 下原 JAR；测试地图从备份恢复。
- 已知限制：版本变化后须重新审计局部槽位和调用签名，不能自动套用。

## P12 · 厨锅迁移和机械配方数据（开发）

- 目标 Farm & Charm 1.1.29、Farmer’s Delight 1.3.4、Let’s Do Compat 2.3.1、Create 6.0.10 及锁定清单中的 Let’s Do 配方来源。
- KubeJS 配方阶段收敛旧锅，按原配方定义生成 FD 等效配方，保留有意义的产量和容器。去掉反向兼容生成结果。Create 使用真正的服务端加工配方。
- 重建：通过 tools/gameplay_inventory.py 盘点来源，tools/gameplay_data.py 生成数据。版本更新后重审锅配方条件、容器、液体标签和旧注册引用。
- 验证与回滚：按本轮报告核对服务端配方和实物出料。移除本轮新增数据并恢复备份，不移除旧锅注册。

## P13 · Bakery 食品配方与原版火药（dev）

- 目标 Bakery 2.1.11、JEI / KubeJS 当前锁定版本、Create 6.0.10。Bakery 的 blank_cake 仅注册方块，添加使用已烘焙的 sponge_sheet 与 chocolate_truffle 的等价工作台路线。保留原方块交互，果酱罐、切分和擀面走原工序，在 JEI 补说明。
- 新增 Create 加热搅拌火药，余烬面粉、木炭、红石各一份，产出一份，保留已有灌注路线。
- 重建：将 pack/kubejs 对应配方 JSON 和客户端 84_bakery_jei.js 复制到 dev。验证加载、实际出料、热条件、JEI 和原容器返还。回滚：删除新增文件后重启 dev。

## P14 · 跨模组饮品在 Vinery 储酒柜的瓶身显示（dev 候选）

- 目标 Vinery 1.5.6，输入为已含 P11 的 JAR（SHA-256 8a4cbcf80fd2089545c769bb1b665dcdd17a56c285cc0bb66b9881a3b53df327）；Brewery 2.1.13；内嵌且实际选用的 Foundation 1.0.7。
- 证据 Vinery BottleRenderer、BigBottleRenderer、WineBoxRenderer 通过 Vinery 自己的 WineBottleBlock.FAKE_MODEL 查询其他模组的 BlockState。Brewery BeverageBlock 独立声明同名属性，默认 true 对应透明模型。Foundation 1.0.7 的 BottleGroupRenderer.stateFor 已通过遍历状态的实际属性按名称将 fake_model 置 false。
- 注入点 三个渲染器各一处 BlockItem.getBlock → Block.defaultBlockState，改为新增客户端桥接类调用 Foundation 现有 stateFor。保留布局、存取、计数、日期、已有 P11 和原渲染后续路径。
- 重建 运行 tools/vinery_storage.py，精确核对输入和嵌套 Foundation 哈希，使用 ASM 9.8 与 tools/VineryStoragePatch.java 构建。仅显式 --apply-dev 时写入本地 dev，输出原 JAR 备份和成员差异记录。
- 验证 检查仅三个类和一个桥接类变化，逐类唯一调用点，P11 类逐字节不变。dev 需比较 Brewery 全部 15 种饮品与 Vinery 酒在大型/中型/小型柜及酒箱的显示和取回。离线通过只代表候选已构建，实际显示待实机。
- 回滚 退出本地 dev 后，用 .stage/vinery-storage/before.jar 恢复 dev 的 Vinery JAR，核对输入哈希。云端与正式实例此次不应用。

- 本轮离线产物 SHA-256 6948bf19bad1584dc4f5bd933ecac522953fd6797decf376ede060862a357a6e。三处替换与桥接字节码已核对，原有 P11 等其他成员逐字节一致。首次构建成员比对错误已保留，修正后通过。应用阶段 Windows 拒绝替换本地 dev 正在使用的 JAR，dev 哈希保持 P11，候选暂存待退出游戏后应用。

- 2026-11-05 已成功应用本地 dev，安装后读回 SHA-256 1224cd6e4e233f9f6c717a34ccb5c8f3d1665b94ca3e005448c7151c2ea028a6，备份仍为 P11 基线。模组锁定清单同步该候选哈希。游戏内实际显示、各柜型与取回验证待下一次 dev 启动。

## P17 · AutoModpack 禁止启动更新时仍加载已安装包（开发，实施前登记）

- 目标 AutoModpack 4.0.7 NeoForge 1.21.1，基线及原始 JAR 哈希见 P15。问题：Preload.updateAll 在 updateSelectedModpackOnLaunch=false 时完全跳过 ModpackUpdater，因此下载到受管目录的模组没有加入 NeoForge 扫描；而此前去重已移除标准 mods 中的副本。
- 注入 Preload.updateAll 的 disabled 分支，调用 ModpackUpdater 新增的只加载方法；从 CheckAndLoadModpack 拆出受管 JAR 加载逻辑，保留原哈希去重，不在该路径调用 applyModpack、清理、下载或更新。已有目录不存在时不加载。启动同步开关的原始语义不变。
- 重建：tools/automodpack_bridge.py 锁定上游 Preload.java SHA-256 14bece9f0abaabf2d58171a4dfb13e7d292c5cc36014e22cba95c8d0317ca450 和 P15 上游输入，精确锚点并将源码收入 LGPL 产物。测试在隔离副本覆盖首次下载、重复文件、重启加载、缺失文件提示、拒绝更新和原目录保留，并检查个人文件。实际 PCL 及联机通过前不发布可交付版本。
- 回滚：退出 dev 后从本次备份恢复 AutoModpack JAR 和客户端配置；受管目录与玩家数据保留。未验证的 P16 网络策略不得视为本项验收通过。

- 2026-11-06 失败补充：真实缺文件更新后 AppleSkin 恢复，但 Tracks 缺通道。标准目录保留 tracks*.jar.disabled；原加载去重把目录下所有文件都算成已加载，包括 disabled/off，因哈希相同而排除了受管 Tracks。实施前扩展范围：loadInstalledModpack 的 standardModsHashes 流仅纳入实际启用的普通 .jar 文件。测试增加禁用副本与同哈希受管文件，必须加载后者。保留该轮 latest.log、失败状态和备份；新候选仅改变此去重条件及版本标记，云端玩法不变。

## P16 · AutoModpack 云服优先和慢源切换（开发，实施前登记）

- 基线：P15 / AutoModpack 4.0.7 NeoForge 1.21.1，原 JAR SHA-256 c76ac8e4c754ba39d1baee3a8ac146be9bfddfad58fa10cc48527d4accd47ce7。仅改变更新器下载策略，不触碰世界、认证、正式实例或玩法。
- 精确注入：DownloadManager.download/downloadTask 优先原生 TLS host，随后已验证项目 GitHub 地址和平台地址；hostDownloadFile/httpDownloadFile 对有备用源的下载按 20 秒窗口检测持续低于 32 KiB/s 并切换。保留文件大小与最终 SHA-1 校验、证书和未知 JAR 警告。修正缓存命中和失败重试的进度计数，以及队列登记先于异步执行。
- DownloadClient.getFreeConnection / Connection.finalBlock：失败传输关闭该连接，使用已确认的 TLS context 和原凭据补建连接，避免取消慢传输后连接永久占用或继续读取旧协议帧。正常连接不变，关闭后的客户端禁止重建。
- 上游源码 SHA-256：DownloadManager.java 738630d76d5292e8150775254c8a45625709f2c8a855bdbde2c85216148cc69f；DownloadClient.java f24fd3809d3b81d96013d6bb788e107c770ed4e272eca11ca8e3cb8c423ef6d3。重建：tools/automodpack_bridge.py（Java 21 目标），精确文本锚点及输入哈希锁定，修改源码随 LGPL JAR 提供。
- 验证：隔离 TLS host / HTTP 慢源测试优先级、回退、连接恢复、缓存、哈希失败；逐成员比较修改范围；最后本地 dev PCL 连接测试由玩家操作，未实机通过不得宣称完成。
- 回滚：退出 dev 后恢复本轮保存的原更新器 JAR；若云端部署则停服恢复其对应备份。受管目录已完成文件保留，删除未完成临时下载由原更新器处理。原生清单及游戏内容不变。

## P15 · AutoModpack GitHub 来源与连接时确认（云端/dev 试点）

- 目标 AutoModpack 4.0.7 NeoForge 1.21.1，原版 SHA-256 c76ac8e4c754ba39d1baee3a8ac146be9bfddfad58fa10cc48527d4accd47ce7。用户已授权云端试点与公开仓库操作，接受受管目录按最新版清理。
- 修改 ModpackUpdater.processModpackUpdate 的已有整合包更新分支，游戏内统一调用 showDangerScreen，取消保持断开且不安装；启动期间更新由客户端 updateSelectedModpackOnLaunch=false 禁用。保留未公开匹配 JAR 的原有警告和确认要求。
- 在 startUpdate 下载队列的每个对象前合并项目固定 GitHub 来源索引中的地址，再保留官方平台地址及原生云服回退。新增 DshReleaseSources，索引只接受本项目仓库 HTTPS Releases 地址，按原生清单 SHA-1 与字节数匹配，不修改 hasPublicMatch 信任判断，原生 DownloadManager 校验继续有效。
- 重建 tools/automodpack_bridge.py，从锁定源码归档和原 JAR 构建，仅替换 ModpackUpdater 类族并新增来源适配类，保留 LGPL 许可证及公开补丁源码/重建方法。Java 编译目标 21，输出暂存目录。
- 验证 原生下载器实际下载 GitHub 试点附件，索引错误和来源不可用时回退；字节码确认 process 通过确认界面且无直接 startUpdate；本地 PCL 及云服加载；游戏内取消、同意、重启与再连接待场景验收。
- 回滚 云端在停服后恢复备份的模组和 automodpack 配置，移除本轮候选。恢复旧客户端配置与原 AutoModpack JAR。试点不处理世界数据；已更新的客户端受管文件用对应旧发布清单恢复。

- 已部署候选来源 GitHub 实验版本 update-pilot-b0f7da3be7b3，SHA-256 6a730659749245c2fae533b7972ad0019998a38e7c06953f7f409c855dd3b3db。本地 dev 与云端同一制品，客户端原模组已备份。云端 229 文件客户端快照只含筛选的模组、资源、脚本、任务定义及地形配置；排除 Skin Restorer、90_probe、个人存档与账号资料。云端在重启后监听 6073，认证及 server.properties 未修改。GitHub 真实附件已通过原生 DownloadManager 下载与哈希核验，屏幕点击与重启联机待实测。
