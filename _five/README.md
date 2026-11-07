# `_five` 工作区索引（先读这个）

本目录只放**验证与交付物**，不是游戏本体。游戏实例在
`C:\Users\Legen\Desktop\游戏\.minecraft\versions\`，本目录的任何改动都不会自动进游戏。

## 目录地图

| 路径 | 内容 | 能否删 |
|---|---|---|
| `MOD_PATCHES.md` | **mod 内部改动登记表（唯一权威）**，升级 mod 前必读 | 不能 |
| `promotion.json` | 主实例所有新增/移除项 + SHA-256 + 回滚方法 | 不能 |
| `回滚说明.md` | 人类可读的回滚清单 | 不能 |
| `audit-roundN.json` | 每次主实例审计快照（存档/文件变化） | 保留最新 3 份即可 |
| `baseline/` | 初始 387 文件哈希 + 受保护存档元数据 | 不能（审计基线） |
| `candidates/` | 已下载并校验过的候选 mod jar 与哈希 | 上线后可删 jar，保留 json |
| `patches/` | **自建补丁 mod 的源码与产物**（P03） | 不能 |
| `backup/` | 被替换/删除的原始文件（如旧 JEI 脚本） | 不能 |
| `runs/` | 每次自动测试的日志与截图（证据） | 报告引用到的不能删 |
| `seasons/`、`weapons/`、`motion/`、`vehicles/`、`combat/`、`enchant/`、`jei/`、`pcl/` | 各专题的探针源码、说明、实测数据 | 说明文档不能删 |
| `archive/` | 已被取代的阶段性状态报告、旧启动脚本、历史截图 | 可删 |

## 规则

1. **改 mod 内部行为**（Mixin / 字节码 / 覆盖 mod 逻辑）→ 必须先写进 `MOD_PATCHES.md`，包含重建与验证步骤。
2. **动主实例** → 更新 `promotion.json`，并跑一次 audit。
3. `runs/` 里的日志是报告引用的证据；删之前先确认没有被 md 引用。
4. 一次性探针脚本请放对应专题目录，别堆在 `_five` 根目录。

## 常用命令

```powershell
# 启动隔离测试实例并自动观察（示例：跑季节生长测试）
python _five/launch_test.py --world five_flat
python _five/watch_test.py GROWTH 240
```
