# 本地 develop 食品与服装批次 · 2026-11-07

基线 `1a889ea`，工作分支 `develop`。文件级安装与检查通过，未启动 Minecraft；出料、容器返还、JEI、服装渲染、装备效果和联机均待实机确认。原有 bridge-verification.json 未提交修改保持原样。

## 安装内容

在本地 dev 内选择 `dreams-and-crusades-local-develop`，从原云服受管包完整复制并逐文件 SHA-256 对比后加入五个官方原始 JAR：Veggies Delight 1.9.3、Crabber’s Delight 1.3.1、Ender’s Delight 1.3.1、CosmeticArmours 1.6.0.1、Patchouli 1.21.1-93-neoforge。版本、官方地址和指纹见 `pack/develop-mods.json`；完整安装锁定见 `pack/mods.lock.json`。

保持 FD 1.3.4、Curios 9.5.1、Create 6.0.10 和 NeoForge 21.1.264。全部声明为 required 的依赖由实际 FML 4.0.45 MavenVersionAdapter 检查通过，包括附属中不带方括号的历史版本声明；没有改动依赖范围。

当前受管模组数为 105。标准 mods 保留更新器入口及原兼容副本，个人文件和世界不进入开发快照。原云服快照完整保留且哈希不变。P18 本地标记使加载器直接加载当前开发快照，不访问云端更新服务；当前选择没有登记远端地址。

**本轮不要连接现有云服测试新增内容。** 云服尚未部署相同模组；服务器握手可能切换回它发布的旧快照。后续联机升级另行安排，不用本地新清单冒充云端已发布内容。

## 精确适配

1. Crabber’s Delight 椰奶 Create 压榨：原结果写成未安装的 `hearthandharvest:coconut_milk`，改为该模组实际注册且灌装配方使用的 `crabbersdelight:coconut_milk`。保留两个椰子产 500 mB，原灌装每瓶消耗 250 mB，不改变成本。
2. CosmeticArmours 镀金下界合金剑鞘：原配方无条件引用可选 CosmeticWeapons 武器，为该精确配方补 `neoforge:mod_loaded` 条件；未安装该武器模组时不加载无效配方，不顺带安装新武器模组。
3. Ender’s Delight 旧刀具标签：将 `forge:tools/knives` 接入现行 `c:tools/knife`，已检查现有定义没有反向引用，不制造标签环。

其余原生 FD 厨锅、砧板、Create 配方与物品 ID 保留。没有发现足以支持强行合并的重复新物品，不新增双向兑换，也不转换玩家库存。原料联动沿用已有 FD 食材与通用标签。

## 重建与检查

需要 Python 3.12、JDK 21 或更高，以及本机现有游戏库。执行顺序：

```powershell
python -B tools/automodpack_bridge.py
python -B tools/develop_food.py
# 审阅暂存记录；关闭 dev 后，仅首次安装执行：
python -B tools/develop_food.py --apply-dev
python -B workflow.py doctor --mods
python -B tools/test_modpack_state.py
```

工具按锁定地址获取文件并核对 SHA-512/SHA-256。已有开发快照拒绝重复应用，防止覆盖开发进度。构建器默认不包含 P16 慢源实验。配方覆盖源码在 pack/kubejs/data，可由工具从锁定原数据重建。

证据保存在 `.stage/develop-food-20261107/`：dependencies.tsv/log、recipe-inventory.json、verification.json、load-test.log、doctor.json、install.json 及 before 备份。静态配方盘点核对了启用模组条件、JSON、可由资源模型佐证的直接输入 ID；并不等同运行时注册表或配方管理器验证。可选兼容配方按已安装模组筛除，仍需后续服务端加载检查。

## 回滚

退出 dev 后运行 `python -B tools/develop_food.py --rollback`。它先验证配置、更新器和三份运行覆盖仍匹配本轮哈希，再恢复旧更新器、旧配置并移除三份新增运行覆盖；若用户已更改文件则拒绝自动回滚。开发快照保留供审计，不递归删除，不操作世界。需要撤销源码时另行回退本轮提交。

本轮没有更新云服、Release、共享库或公开附件，也没有重建/迁移任何世界。
