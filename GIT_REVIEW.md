# Git 首推审阅

本地基线仅追踪由本文件旁的 [git-allowlist.txt](git-allowlist.txt) 列出的文件。首推前用 `git ls-tree -r --name-only HEAD` 审核实际提交，用 `git status --short` 核对本地工作。

纳入范围为工作流工具与入口、审阅过的 FTB Quests / KubeJS / Flywheel 配置、模组指纹、自有 NBT 工具与选定建筑源文件、现行补丁记录及性能 harness 源码。

排除范围为任何存档、实例快照、账号/PCL 运行数据、第三方 JAR 和上游移植源码、JFR、运行日志、截图、已构建结构、缓存、备份、暂存输出和 P07 实现。二进制蓝图待来源和分发权审阅后逐项放行。清单中的 JAR 元数据 URL 仅为来源线索，下载前需核对官方版本和实际文件 SHA-256。尚未补齐逐个制品的已验证下载链接，不能凭此清单自动重建整包。

干净检出可以运行离线样例。现有运行验收仍依赖本机 Java/PCL、dev 实例、经校验的本地快照和探针数据。按 DEV_INSTANCE 的规则管理这些材料。历史文档指向的证据可在原本地工作区查看。

2026-11-07 用户明确选择公开并复用 `LegendaryGaoZheng/dreams-and-crusades-releases`。develop 分支保存审阅过的源码快照，main 保留发布入口与 Markdown 版本记录；安装附件使用 GitHub Releases。首次同步的 167 个追踪文件逐个 Git blob 哈希核对通过，包含五张自有任务书图片。源码快照不是可直接安装的完整整合包。

本地 origin 已登记该仓库。首次通过连接器导入当前源码快照，远端 develop 基于原发布仓库历史，本地开发历史继续保留；没有设置 upstream，也没有强制覆盖任何分支。以后同步先核对两侧历史，不直接 force push。未提交修改没有被夹带上传。

任何后续正式 Release 必须先提交 releases/<版本号>.md，并用同一份 Markdown 作为 Release 正文及附件内说明。模组 JAR、第三方资源包和自改制品仍逐项核对分发许可。发布清单生成器要求 --notes，发布与正式地图迁移继续分别确认。
