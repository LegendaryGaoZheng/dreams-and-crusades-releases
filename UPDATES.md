# 增量更新试点

发布仓库为 https://github.com/LegendaryGaoZheng/dreams-and-crusades-releases 。已核对 Public 和账号所有权，首批公开文件只有发布说明。

## 已实现与限制

本轮验收未通过。直接调用原生 ModpackUpdater.deleteNonModpackFiles 的隔离测试证实，它会删除管理目录中从未列入旧版本清单的 personal-notes.txt。目录外的存档和 options.txt 保持原字节。这与只删除上一版登记文件的要求不符，保留 native-07/deletion-policy.txt 与完整日志，云端推广暂停。配置 allowRemoteNonModpackDeletions=false 只控制额外远程删除请求，不能改变该管理目录清理。后续需决定接受其隔离目录规则，或改为启动 PCL 前的独立白名单更新器。

本地 dev 安装 AutoModpack 4.0.7 NeoForge 1.21.1。该版本来源和 SHA-256 已加入模组锁定清单。候选客户端关闭自更新、自动切换加载器及远程非整合包删除。原生组件试验在 Java 25 和本机 Netty 4.2.16 等只读依赖下运行了原生清单生成、TLS 服务和 DownloadManager，不启动 Minecraft。证据及失败轮次在 .stage/update-pilot 下，汇总见 pack/update-pilot/verification.json。

验证通过两版清单、新增、替换、相同文件零传输、残缺文件重下、哈希不匹配重试后拒绝和删除失败文件。这里只证明传输与清单机制。用户已确认 PCL 能进标题页，日志核验 AutoModpack 预加载和主加载成功。加载器清理已实测但不符合约定；实际断网恢复、完整整合包和公网联机待验收。测试只在本地阶段目录写入样例及测试证书。

4.0.7 使用自定义传输协议，GitHub Releases 附件不能替代清单服务。5.0.0-rc.7 提供静态 HTTP 导出，但它仍是预发布，且要求 head、journal、objects 路由，普通附件 URL 不能直接等同该服务。目前选择稳定 4.0.7 候选，GitHub 用于版本说明和发布附件。要实现公网增量更新仍需通过验证的 AutoModpack 主机，或另行决定更新器方案。

用户提供的云鸢端口 6073 当前拒绝 TCP 连接。它在早先面板中曾标为 RCON。启用下载服务前核对当前 RCON 未占用，并确认端口确实分配给本实例。公网 80/443 可连接只能证明节点有服务，不能据此建立属于本实例的 HTTPS 下载源。当前云端没有部署更新模组。

## 复核入口

先安装 Python 3.12，并准备本机 Java 与现有游戏依赖，运行原生试点：

```powershell
python -B tools/update_pilot.py
```

脚本校验并按需下载固定版本，每轮在 .stage/update-pilot/native-NN 新目录运行。文件样例为工具生成的文本。原生测试会生成本机测试证书和私钥，均不入库。

发布清单生成器使用显式审阅清单，不递归纳入整个游戏实例。列表元素为 path、可选 url，以及自有附件的 redistribution_approved 标记。指定官方 HTTPS 下载地址时不把第三方文件复制进附件目录。自有附件使用 SHA-256 命名，便于镜像和核验。

```powershell
python -B tools/release_manifest.py --selection <审阅清单.json> --version 1.0.3
python -B tools/release_manifest.py --selection <审阅清单.json> --version 1.0.4 --previous <上一版manifest.json>
```

输出在 .stage/releases/<版本>。已存在版本拒绝覆盖。manifest.json 包含相对路径、大小、SHA-256、下载 URL 和删除项的旧哈希。它是发布审阅格式，AutoModpack 自己的清单由原生工具生成。上传版本附件前需确认版本、清单与分发权。更新工具应在旧文件哈希匹配时执行删除；本期生成器不执行客户端文件安装。

## 玩家手操与后续验收

1. 正常退出旧游戏，从 PCL 启动本地 dev。确认能到标题页，日志中 AutoModpack 正常加载。
2. 当前没有可连接的公网更新主机，先继续使用原来的服务器连接。云端试点部署需要单独确认，不能把样例文本清单当成整个整合包发布。
3. 公网试点需要冻结一份经审阅的完整客户端 payload，加入客户端专用模组、自有 KubeJS、资源与指定配置，并验证受管理路径。禁止直接同步当前服务器目录或整个 dev。
4. 部署前在云鸢核对 6073 的分配与 RCON 设置。pack/update-pilot/automodpack-server.json 是可审阅候选，关闭自动发布，客户端更新保持可选，不应直接当成生产配置启用。
5. 启用后比对首次连接的证书指纹，完成两版本更新、旧模组清理、断网恢复、个人文件保留和实际联机，再由服主确认下一版正式发布。

回滚本地候选时先退出 dev，核对 AutoModpack JAR 为锁定哈希后移除，撤销新增客户端试点配置及锁定条目。用户若在测试后修改配置，先保存差异。云端仍按当前配置运行，整合包发布与存档迁移分别确认。

## 2026-11-05 更新需求确认

用户接受受管理目录按最新版清理，之前删除策略失败保留为历史证据，不再作为新约定下的阻塞。个人存档、Xaero、截图、按键和画质仍置于受管范围外。本地 dev 和候选客户端配置已设置 updateSelectedModpackOnLaunch=false，取消启动期间自动应用整合包更新；4.0.7 的预加载仍可能查询元数据。用户优先要求连接服务器发现版本差异时提示并可选择更新。原生 4.0.7 对已有且全为官方匹配文件的更新会直接 startUpdate，无法单凭该设置保证每次确认。其 FetchManager 只查询 Modrinth/CurseForge，GitHub Releases 需要额外来源适配。5.0.0-rc.7 支持 HTTP 合约，但普通 Releases 附件 URL 仍需路由转换，并且是预发布。两条路线均不得作为已经交付的公网自动更新宣称。

## GitHub 来源适配试点 dsh1

已实现 P15。来源桥接源码与自动重建流程在公开发布仓库 bridge/，采用 LGPL-3.0，原有许可证和完整修改源码嵌入 JAR。GitHub Actions 自动构建并发布实验附件，根 update-sources.json 指向固定版本。首轮发布脚本失败的日志保留，后续工作流成功。

实验版本为 https://github.com/LegendaryGaoZheng/dreams-and-crusades-releases/releases/tag/update-pilot-b0f7da3be7b3 。它包含客户端引导 JAR、来源适配记录和无玩法效果的探针资源，不是整合包正式版本。完整客户端快照保存在云端私有 AutoModpack 目录，未将第三方模组集合公开上传到 GitHub。

本地 dev 与云端安装 SHA-256 6a730659749245c2fae533b7972ad0019998a38e7c06953f7f409c855dd3b3db 的同一候选。229 文件、211918572 字节的云端客户端快照冻结于当前云服内容，补入 23 个客户端专用模组及 dev 客户端脚本。它是云服现有内容的试点基线，后续 gameplay dev 改动不会自动纳入。地形配置取云端，排除 Skin Restorer 和 90_probe。客户端个人数据不在清单内，首次试点前已备份本地 dev 的 101 个 JAR。

源码适配使已有整合包的游戏内更新分支也经过原有确认界面，保留取消和自改 JAR 警告。客户端 updateSelectedModpackOnLaunch=false。来源索引匹配原生清单 SHA-1、字节数，HTTPS 地址限定本项目 Releases。索引缺失或下载失败时保留原平台及云服回退。真实 GitHub 附件已由原生 DownloadManager 成功下载，错误大小和其他仓库来源被拒绝。首次参与的朋友需要先安装引导 Mod，后续才具备游戏内更新能力。Minecraft 或 NeoForge 版本变更仍需单独升级启动器实例。

云端 updater 配置监听 6073，关闭强制要求所有玩家安装的选项。host-modpack/main 使用独立冻结副本，syncedFiles 为空，避免服务器运行目录变化自动进入发布。启动时仅重建该固定快照的原生清单。server.properties 原字节未改，等待面板重启加载。重启后核对日志、6073 可达、首次提示、取消后无安装、确认后下载、游戏退出重启并再次连接。镜像未配置，本轮使用 GitHub 直链及云端回退。

回滚先由用户正常退出 dev 和停止云服。恢复 .stage/update-pilot/before-client-mods 中的原客户端模组，云端移除本轮新增 AutoModpack JAR，并将 automodpack 试点目录保留归档以便审计。云端玩法模组与存档无迁移。已被原生更新器改动的本地受管文件从备份恢复。

用户要求提高下载速度后，云端配置及候选配置将 bandwidthLimit 从 2 Mbps 改为 0（取消软件限速），保留旧配置备份。当前下载服务需先 config reload，再 host restart 才会使用新限速；正在下载时重启下载服务会中断当前连接。云鸢公开套餐页未列出实例公网带宽，套餐总带宽尚未确认。

## 2026-11-05 受管模组加载修复（测试中）

基线 dsh1，用户首次更新后，原生去重从标准 mods 目录移除重复文件；updateSelectedModpackOnLaunch=false 同时跳过了预加载路径，导致受管 JAR 未加载。已从原始逐哈希备份恢复 96 个本地模组。P17 候选将受管模组加载与更新操作分离；默认构建不包含尚未验证的 P16 下载策略。

本地 dev 候选 SHA-256 9d7feb77f5a66069ecde6da71518bddb58d1d145cba5ac941e4534c622394c74；原 dsh1 与安装记录保存在 `.stage/update-pilot/p17-client-install/`。回滚先退出游戏，检查现有文件哈希后将 before.jar 恢复至 dev 的 AutoModpack JAR。云端未替换此候选。

隔离 Java 测试 load-test-03 调用实际加载和更新检查方法，通过受管 JAR 加载、相同哈希去重、文件不变、相同文件跳过、缺失和更改检测。用户确认本地 PCL 能直接连接，日志确认候选 JAR 和标准 mods 加载；缺失文件的公网下载、重启后受管加载、其他玩家的干净安装和版本变更发布流程仍待验收，不应向朋友宣称自动更新已可交付。

## 2026-11-06 缺文件与引导包验收（进行中）

用户已确认 P17 本地候选直接连服成功。native-10 原生 TLS 隔离测试通过两版新增、替换、相同文件不传输、残缺修复和错误哈希拒绝；保留受管目录清理的历史 POLICY_FAIL 标记，不将其篡改为成功，用户现已接受该目录清理语义。

真实缺文件测试：从普通 mods 与受管 mods 两处暂移 AppleSkin（SHA-1 81cf0e668f991f83ac8820c386fbd6c9c3602246），逐哈希备份于 `.stage/update-pilot/missing-mod-20261106/`。等待 PCL 连接触发下载及重启验收；测试中断时退出游戏后按 record.json 恢复两处文件。

公开试验附件：[update-pilot-13a0b441a332](https://github.com/LegendaryGaoZheng/dreams-and-crusades-releases/releases/tag/update-pilot-13a0b441a332)。GitHub Actions 成功构建，ZIP 下载检查通过，仅含更新器 JAR、空客户端选择配置、公开 known-hosts 和安装说明。发布 JAR SHA-256 bda1c53e985e90cbf727f63a236992bf731e592b4bcb61b7edb81d442c1e3c0d（Java 21 构建与本地编译器产物哈希不同）。云端只读核验现有 cert.crt 的指纹仍为 3c654485e5f58c0c261c99f1d98c56886b9da2d8ab0fc539c51762a75f14c195。

引导 ZIP 仅用于独立的新 PCL 实例。已有玩家只替换更新器 JAR，不能用空客户端配置覆盖已有状态。该附件仍为 prerelease，干净客户端完整安装、下载中断与跨发布验收尚未完成。

### 缺文件试验失败与修正

用户确认 AppleSkin 下载后重启仍连服失败。日志显示缺少 Tracks 三个通道，受管清单与 JAR 本身齐全。根因：标准目录中的 `tracks*.jar.disabled` 被原哈希去重误算为启用文件，从而抑制受管 JAR 加载。失败原始日志和此前候选备份在 `.stage/update-pilot/tracks-failure-20261106/`，不将此轮记为成功。

P17 加载时只统计标准目录内实际普通 .jar。load-test-04 增加同哈希禁用副本，实际加载方法测试通过。检查本地目录确定受管 Tracks 加入待加载列表。新候选 SHA-256 c9bf0a5a4e82f3e5ca5045ac75a32bdc8e58577bde5ca24ebd21f09b13f84b8d，已安装本地 dev，等待 PCL 再连接。此前 GitHub 引导附件尚不含此修正，不向朋友推广该旧附件。

2026-11-06 20:32 用户确认修正后成功进入。日志核验 AppleSkin 与 Tracks 均通过 EarlyModLocator 加载，服务端清单一致并加载 4142 个成就。真实缺文件下载、重启及受管模组加载这一轮通过；原失败日志与成功复验日志分别保留。修正版公开试验附件为 update-pilot-be0e544c9331，GitHub Actions 已成功构建。干净玩家首次安装、实际下载中断恢复和新云服版本发布演练仍待验收，不能扩大此轮证据范围。

## 统一模组管理规则（2026-11-06，已复验）

云端冻结客户端快照与本地受管清单是内容依据。Skin Restorer 原先只在运行目录，不归快照管理；现将同哈希文件加入云端客户端 payload，经用户执行 automodpack generate 后核对：仅新增该文件，无其他更改，清单共 230 个文件、100 个模组。游戏退出时同步本地清单与受管 JAR，再移除本地标准目录的对应副本。用户确认可以连服且皮肤正常。

- 模组内容全部归受管清单管理。标准 mods 只保留更新器启动入口，以及 Kotlin For Forge、MezzConfig、Sodium 的必要兼容副本；兼容副本必须与受管版本哈希相同，不独立更新。
- 运行 `python -B workflow.py doctor --mods` 只读检查：管理文件缺失、哈希不同、标准目录清单外 JAR、重复副本冲突、多余受管 JAR。禁用文件不算启用模组。检查失败退出码为 1。也可直接运行 tools/modpack_state.py --instance <实例>。
- 发布入口 tools/release_manifest.py 对显式选择的 mods 输入先解析受管清单，缺失或冲突时拒绝生成。不会再只从标准 mods 递归打包，也不会把两个目录当成两个版本。
- 新增模组先进入 dev 受管内容并记录版本；正式供玩家使用前冻结相应云端客户端快照并生成新清单。直接更改云服运行 mods 不等于已发布客户端更新。更新器自身单独固定版本，普通模组和玩家个人文件分别管理。

本轮备份、原云端清单、前后审计在 `.stage/update-pilot/consistency-20261106/`。回滚需退出 dev，恢复 client-manifest-before.json 和 skinrestorer-before.jar 至原运行路径，并仅在当前受管 Skin Restorer 哈希仍匹配时移除其副本；云端删除本轮新增的客户端 payload Skin Restorer 后重新 generate，服务端运行 JAR 不动。

工具临时目录测试覆盖标准禁用文件、受管缺失、冲突、副本、多余文件与路径越界。工具验收不替代前述仍待进行的干净玩家安装及断网恢复。
