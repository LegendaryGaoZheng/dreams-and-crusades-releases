# 梦想与远征

Minecraft 1.21.1 / NeoForge 21.1.264 / Java 25 / PCL。这里是源码、工具和交付记录。运行实例位于本机游戏目录。首次接手读 [AGENTS.md](AGENTS.md)、[工具盘点](TOOL_INVENTORY.md) 和 [入库审阅](GIT_REVIEW.md)。旧编号文档是历史记录。

## 通用入口

从仓库根运行。Python 3.12 和 Git 足以运行下列离线样例。历史建筑预览另需 Pillow、配套资产和已核验输入。

```powershell
python -B workflow.py doctor
python -B workflow.py plan quest --id 74DF9E2A6EAD17BD --title "领取初始补给"
python -B workflow.py stage quest --id 74DF9E2A6EAD17BD --title "领取初始补给"
python -B workflow.py stage building
python -B workflow.py verify quest --artifact <输出的-stage-目录>
python -B workflow.py verify building --artifact <输出的-stage-目录>
python -B workflow.py verify perf
```

`plan` 输出源文件和候选内容的哈希。每次 `stage` 使用新目录，生成内容和 `record.json`。任务标题默认编辑 `en_us`（当前主翻译含中文），按原 ID 精确改一行。应用到 dev 时把同一命令加 `--apply-dev`，先关闭游戏，并确认 dev 源文件哈希仍等于仓库基线。应用会保存 `before.snbt`。回滚时先核对 dev 文件仍等于此次输出哈希，然后在游戏退出时恢复该备份。验证通过的修改可将输出纳入源码提交。建筑样例是可离线重建的两格路标结构。

性能预检使用本机现有快照。显式加 `--pilot` 才调用旧 harness 做 dev 工具诊断。该调用按旧 harness 契约重新布置 dev 配置及专用地图，先备份或提交已有 dev 工作。每次 pilot 结果独立保留，不作为性能收益。重新开始正式对照时另行制定测试批次。

## 任务流程

| 工作 | 离线处理 | dev 验收与回滚 |
|---|---|---|
| 模组增删 | 对照 [当前模组指纹](pack/mods.lock.json)，核对来源、版本、依赖、端别和存档影响 | 用测试副本启动 PCL，验证受影响玩法与联机组合。回滚清单、JAR、配置及测试快照 |
| Bug、功能与适配 | 记录复现、日志、期望与最小差异。自有脚本基线在 pack，修改内部行为前登记 [MOD_PATCHES.md](_five/MOD_PATCHES.md) | 用相同复现验证并回归邻近玩法。回滚对应补丁及配置 |
| 建筑蓝图 | 用现有 NBT 读写器检查尺寸、方块、方块实体和依赖。候选先放暂存目录 | 成批验收放置、朝向、机械与外观。保留上一版结构 |
| FTB Quests | 现行任务文件在 pack/quests。修改图时核对 ID、依赖、环、物品和奖励注册；标题命令保留图和进度 ID | 成批检查显示、解锁、奖励及已有进度。恢复上一版任务定义 |
| 性能 | 先读 [收尾报告](_five/perf/FINAL_PERFORMANCE_REPORT.md) 并离线筛候选 | 同快照和画质跑场景，至少三次交替复测。比较平均帧、1% low、长帧并做正确性回归 |

历史任务生成器要求 `--chapters` 指向 `.stage` 下新建的独立章节副本。它们可能重写依赖或重复追加内容，预览差异后才挑选改动。不要把生成器输出直接覆盖现行任务书。

交付记录至少包含任务、基线提交或哈希、实际文件差异、验证方式与结果、失败证据和回滚。分支上完成单项工作，验证后合入 main。

## 联机皮肤

云端 dev 与本地 dev 安装 Skin Restorer 2.11.0 NeoForge，来源与 SHA-256 见模组锁定清单。变更基线为 `2bdd38d`。两处 JAR 哈希一致，已核对模组声明支持 Minecraft 1.21.1。云端保留 `online-mode=true`。云端重启后验证加载和皮肤显示。回滚时移除两处对应 JAR，撤销锁定清单条目，并重启对应实例。

## LTAB 建筑食物战利品

基线 `85c9ae0`。使用本地 dev 的 Create: Let The Adventure Begin 4.1.0 和 Let’s Do JAR，安装 Python 3.12 的 `nbtlib` 后运行：

```powershell
python -B tools/ltab_food.py --dev 'C:/Users/Legen/Desktop/游戏/.minecraft/versions/梦想与远征_dev'
```

生成到 `.stage/ltab-food`。在同一命令追加 `--apply-dev` 可布置到本地 dev。重建或打包时将该目录的 `data` 并入 KubeJS 的 `data`。模板由原版附属 JAR 本地生成，Git 记录生成器，保留来源和输入哈希。

离线核对 41 个模板、82 个输出，每个模板只更改一个箱子或木桶的战利品表引用。原池保留，每个新池抽取一次。容器坐标、原表、新表、概率和输出哈希在 `.stage/ltab-food/record.json`。本轮跳过生成池未引用的模板、需要新增容器的结构、只有陶罐的红树林小屋，以及用途尚待确认的地牢、采石场、废墟和城堡酒窖。首次开箱和房间动线待 dev 实测。变更面向后续生成的结构，现有存档容器不批量改写。

回滚时先根据 `record.json` 核对 dev 中对应文件的 SHA-256，再删除本轮新增的 82 个覆盖文件。已生成且尚未开过的箱子可能引用新表，已用于游玩的测试地图用升级前快照回滚。

增量发布试点、原生组件测试和 PCL 手操入口见 [UPDATES.md](UPDATES.md)。

AutoModpack 接管后，模组清单一致性使用 `python -B workflow.py doctor --mods` 检查。受管包清单为模组内容来源；标准 mods 中的更新器是启动入口，同哈希兼容副本不是另一个版本。禁止凭标准目录数量判断整合包完整性。发布工具已支持受管目录解析，仍须显式选择发布文件，详情见 UPDATES。

本地 `develop` 的三款食品附属和 CosmeticArmours 安装、静态验收与回滚见 [DEVELOP.md](DEVELOP.md)。当前选择为独立本地开发快照，尚未发布到云服。

正式发布必须附带 [Markdown 版本说明](CHANGELOG.md)。发布清单生成器现要求 `--notes releases/<版本号>.md`，并将同一份说明写入发布产物，供 GitHub Release 使用。
