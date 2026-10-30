<div align="center">

# 🛡️ AgentCubicle

**给 AI Agent 的一间隔音工位：先裁决，再动手，全程留痕。**

[简体中文](README.md) · [繁體中文](README.zh-TW.md) · [English](README.en.md) · [日本語](README.ja.md)

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)
![Dependencies](https://img.shields.io/badge/dependencies-zero-2ea44f)
![License](https://img.shields.io/badge/license-MIT-yellow)
![Offline](https://img.shields.io/badge/offline-first-blue)
![Tests](https://img.shields.io/badge/tests-83%20passing-brightgreen)
![Platform](https://img.shields.io/badge/platform-Win%20%7C%20macOS%20%7C%20Linux-lightgrey)

[📦 Release 下载](https://github.com/gitstq/AgentCubicle/releases/latest)

</div>

---

## 🎉 项目介绍

当 Agent 拿到一台「电脑」之后，真正的问题才刚开始：它**改了哪些文件、跑了什么命令、连了哪些网站**？出事之后，日志能不能作为证据？

AgentCubicle 就是为这个问题而生的。它不是又一个 Agent 框架，而是**架在 Agent 与真实世界之间的那道闸门**：

- 🧊 **Cubicle（工位）**：每个 Agent 领到一个独立的隔离目录，读写范围被钉死在里面；
- 🛡️ **前置裁决**：任何动作在执行前必须先过策略引擎，得到 `allow` / `deny` / `ask`，并附带**可解释的理由和命中的规则**；
- ⛓️ **防篡改审计**：每条记录都串在 SHA-256 哈希链上，改一条，后面全断，一验便知。

**解决的核心痛点**

| 痛点 | 传统做法 | AgentCubicle |
| --- | --- | --- |
| Agent 误删/误改宿主文件 | 靠 prompt 里写「不要乱动」 | 路径白名单 + 逃逸检测，**硬拦** |
| 出事后无法还原经过 | 翻 stdout 日志 | 哈希链审计，可校验、可回放 |
| 日志本身可被篡改 | 无解 | 篡改即断链，`audit --verify` 秒级发现 |
| Agent 无限调用/疯狂写盘 | 事后看账单 | 动作数 / 字节数 / 时长**三重预算** |
| 引入安全工具反而带来一堆依赖 | `pip install` 一堆包 | **零第三方依赖**，纯标准库 |

**自研差异化亮点**

- 🪶 **真·零依赖**：只用 Python 标准库，`auditwheel` 级别的环境洁癖患者也能用；完全离线，不发一个网络包。
- ⛓️ **哈希链而非普通日志**：这是本项目的核心原创点。审计不是"记录一下"，而是**密码学上可验证的_append-only 链_**，任何事后修改（哪怕重算哈希）都会被断链检测抓到。
- 🧠 **可解释裁决**：每次裁决都返回 `reason` + `rule` + `risk`，不是黑箱 `True/False`，方便直接回喂给 LLM 做自我修正。
- 🧪 **Dry-run 预检**：动真格之前先 `check` / `dry_run` 批量试裁决，零副作用。
- 🚫 **纵深防御**：除了策略 deny 列表，还内置一组「管道进 shell / 命令替换 / 写块设备 / fork bomb」高危模式，**即使策略写漏了也能兜底**。

**灵感来源**：GitHub Trending 上 `OpenMausBot`（每个 bot 拥有自己的电脑、动作先决策后记录）与 `t3code`（Agent 控制面）的产品思路。二者都是重型的 Electron / 桌面栈且依赖云服务，AgentCubicle 则把同样的安全模型**压缩成一个零依赖的终端 CLI**——代码 100% 自研，未复用其任何实现。

---

## ✨ 核心特性

- 🧊 **隔离工位**：`init` 一个 cubicle 就得到 `workspace/`、`tmp/`、`output/`、`audit/` 四件套，Agent 的活动半径一目了然。
- 🛡️ **策略前置裁决**：`file.read` / `file.write` / `file.delete` / `shell.exec` / `net.fetch` 五类动作全覆盖。
- 🚦 **三态决策**：`allow`（放行）/ `deny`（拒绝）/ `ask`（需人工确认），每条都带理由与命中规则。
- ⛓️ **防篡改审计链**：`prev_hash + sha256`，`audit --verify` 一键验真，精确到「第几条、哪个哈希对不上」。
- 🧱 **路径逃逸防护**：`../../`、绝对路径、符号链接逃逸一律拒绝，策略规则在归一化后的 **posix 相对路径**上匹配，跨平台行为一致。
- 💣 **危险命令兜底**：`curl x | sh`、`` `cmd` ``、`$(...)`、`> /dev/sda`、`rm -rf /`、fork bomb 等模式**策略之外**额外拦截。
- 📊 **三重预算**：动作次数、写入字节数、运行时长，超限即拒，杜绝失控循环。
- 🧾 **多格式报告**：`text` / `markdown` / `json` 三种审计报告，可直接塞进 CI 产物或人工复核。
- 🧪 **零副作用预检**：`cubicle check` 与 `Guard.dry_run()` 只裁决不执行。
- 🔌 **CLI + 库双形态**：既能 `cubicle run demo -- ls`，也能 `from agentcubicle import Guard` 嵌进你自己的 Agent 循环。
- 🖥️ **跨平台**：Windows / macOS / Linux 通吃，Python 3.8 起。
- 🧩 **环境清洗**：子进程只继承 `PATH`/`HOME` 等必要变量，宿主凭据不会泄漏给 Agent。

---

## 🚀 快速开始

### 环境要求

| 项目 | 要求 |
| --- | --- |
| Python | **3.8 及以上**（3.11 / 3.12 已实测） |
| 第三方依赖 | **无** |
| 操作系统 | Windows / macOS / Linux |
| 磁盘 | 每个 cubicle 约几 KB（不含你的产出） |

### 安装

**方式一：从源码（推荐，零构建工具依赖）**

```bash
git clone https://github.com/gitstq/AgentCubicle.git
cd AgentCubicle
python -m agentcubicle --version     # 无需安装即可直接用
```

**方式二：pip 安装（带 `cubicle` 命令）**

```bash
git clone https://github.com/gitstq/AgentCubicle.git
cd AgentCubicle
pip install .
cubicle --version
```

**方式三：从 Release 附件安装**

```bash
pip install https://github.com/gitstq/AgentCubicle/releases/latest/download/agentcubicle-1.0.0-py3-none-any.whl
```

### 60 秒上手

```bash
# 1️⃣ 建一个工位
cubicle init demo

# 2️⃣ 动手前先问一句（零副作用）
cubicle check demo file.write workspace/notes.txt
# ✅ ALLOW  file.write  workspace/notes.txt

# 3️⃣ 真正写入
cubicle write demo workspace/notes.txt --data "hello agent"

# 4️⃣ 在工位里执行命令
cubicle run demo -- echo hello

# 5️⃣ 试试越界（会被硬拦）
cubicle check demo file.write ../../.bashrc
# ⛔ DENY  path escapes the workspace root

# 6️⃣ 校验审计链有没有被人动过手脚
cubicle audit demo --verify
# ✅ audit chain intact — no tampering detected
```

### 作为 Python 库使用

```python
from agentcubicle import Cubicle, Guard

cubicle = Cubicle("demo")
if not cubicle.exists:
    cubicle.create()

guard = Guard(cubicle, actor="my-agent", session="s-001")

result = guard.write_file("workspace/report.txt", b"hello")
print(result.decision.effect)   # allow / deny / ask
print(result.decision.reason)   # 可解释理由
print(result.decision.rule)     # 命中的策略规则

# 批量预检：只裁决，不执行
for d in guard.dry_run([("file.write", "workspace/a.txt"),
                        ("file.write", ".env")]):
    print(d.effect, d.reason)
```

---

## 📖 详细使用指南

### 命令总览

| 命令 | 作用 |
| --- | --- |
| `cubicle init <name>` | 创建隔离工位 |
| `cubicle list` | 列出所有工位 |
| `cubicle info <name>` | 查看工位详情（策略、审计条数、链状态） |
| `cubicle rm <name> --yes` | 删除工位 |
| `cubicle check <name> <action> <target...>` | **事前裁决**，零副作用 |
| `cubicle run <name> -- <command>` | 受策略约束地执行命令 |
| `cubicle write <name> <path> --data <text>` | 受控写文件（`--data` 省略则读 stdin） |
| `cubicle read <name> <path>` | 受控读文件 |
| `cubicle audit <name> [--tail N] [--verify]` | 查看 / 校验审计链 |
| `cubicle report <name> [--format text\|markdown\|json]` | 生成审计报告 |
| `cubicle policy <name>` | 查看当前策略 |

全局参数：`--base <dir>`（覆盖默认的 `~/.agentcubicle` 根目录，**子命令前后都可用**）、`--version`。

### 五类动作

| action | 含义 | target 示例 |
| --- | --- | --- |
| `file.read` | 读取文件 | `workspace/a.txt` |
| `file.write` | 写入文件 | `output/report.json` |
| `file.delete` | 删除文件 | `tmp/cache.bin` |
| `shell.exec` | 执行命令 | `git status` |
| `net.fetch` | 网络访问 | `https://api.github.com` |

### 工位目录结构

```
~/.agentcubicle/cubicles/<name>/
├── policy.json          # 策略文档（可直接编辑）
├── cubicle.json         # 元信息
├── workspace/           # Agent 主战场（默认可写）
├── tmp/                 # 临时目录（默认可写）
├── output/              # 产出目录（默认可写）
└── audit/audit.jsonl    # 哈希链审计日志
```

> ⚠️ **路径基准**：所有相对路径都以 **cubicle 根目录**（上图中的 `<name>/`）为基准，而不是 `workspace/`。所以 `workspace/notes.txt` 落到磁盘就是 `<name>/workspace/notes.txt`。

### 策略配置

`cubicle init` 后编辑 `policy.json` 即可。完整结构（默认值）：

```json
{
  "version": 1,
  "name": "default",
  "default_effect": "ask",
  "paths": {
    "read_allow": ["**"],
    "read_deny": [".git/config", "**/.ssh/**", "**/.aws/**"],
    "write_allow": ["workspace/**", "tmp/**", "output/**"],
    "write_deny": [".env", "**/.env", "**/.git/**", "**/.ssh/**", "**/*.pem", "**/*.key"],
    "delete_deny": ["**"]
  },
  "commands": {
    "allow": ["ls*", "cat *", "echo *", "pwd", "git status*", "python -m pytest*"],
    "deny": ["rm -rf *", "sudo *", "chmod 777 *", "curl *", "wget *"]
  },
  "network": {
    "allow_hosts": [],
    "deny_hosts": ["*"]
  },
  "budgets": {
    "max_actions": 200,
    "max_write_bytes": 10485760,
    "max_runtime_seconds": 600
  }
}
```

**字段说明**

| 字段 | 说明 |
| --- | --- |
| `default_effect` | 没有任何规则命中时的兜底取值，推荐 `ask`（保守）；设 `deny` 则变成最严格的白名单模式 |
| `paths.*` | glob 规则。**写 `docs` 等价于 `docs/**`**，会自动覆盖其下所有内容 |
| `commands.allow/deny` | 命令 glob，先匹配 deny 再匹配 allow；deny 优先 |
| `network.allow_hosts/deny_hosts` | 主机名 glob，自动忽略大小写、端口与路径 |
| `budgets.*` | 三重预算，`0` 表示不限制 |

> 🔐 **合并语义**：你的策略会**深度合并**到内置默认策略之上，且**列表字段是覆盖而非追加**——这是安全工具的 fail-safe 取向，收窄白名单一定生效。

校验一份策略文件是否合法：

```bash
cubicle policy --policy-file ./my-policy.json
```

### 典型场景

**场景一：给 CI 里的 Agent 上枷锁（最严格白名单）**

```json
{
  "default_effect": "deny",
  "paths": { "write_allow": ["output/**"] },
  "commands": { "allow": ["python -m pytest*"] },
  "network": { "deny_hosts": ["*"] },
  "budgets": { "max_actions": 30 }
}
```

**场景二：允许访问特定 API**

```json
{ "network": { "allow_hosts": ["api.github.com", "*.openai.com"], "deny_hosts": [] } }
```

**场景三：把裁决结果回喂给 LLM 自我修正**

```python
result = guard.write_file("workspace/x.txt", b"data")
if not result.decision.allowed:
    prompt_hint = f"Action denied: {result.decision.reason} (rule={result.decision.rule})"
```

**场景四：CI 归档审计报告**

```bash
cubicle report demo --format markdown --output audit-report.md
cubicle audit demo --verify || exit 1      # 链断了直接让流水线失败
```

### 退出码

| 退出码 | 含义 |
| --- | --- |
| `0` | 成功 / 允许 |
| `1` | 运行错误（工位不存在、审计链断裂等） |
| `3` | **动作被策略拒绝** |
| 子进程退出码 | `cubicle run` 会透传被执行命令的退出码 |

---

## 💡 设计思路与迭代规划

### 设计哲学

1. **拒绝也要留痕**。被拦下的动作同样写入审计链——「谁在什么时候试图越界」往往比「谁做了什么」更有价值。
2. **可解释优先于可执行**。返回 `reason + rule + risk` 而不是一个布尔值，让 Agent 有能力理解边界并自我纠正，而不只是一头撞墙。
3. **默认保守**。默认策略允许自由读取、限制写入范围、禁用网络；`default_effect` 默认 `ask`。想宽松，请显式声明。
4. **纵深防御**。不把安全寄托在「用户策略写得对」上：路径归一化 + 逃逸检测 + 高危模式兜底 + 环境清洗，四层叠加。
5. **零依赖是一种安全属性**。依赖越少，供应链攻击面越小，审计成本越低。

### 为什么用哈希链而不是普通日志

普通 JSONL 日志被改一行，没人看得出来。哈希链让每条记录携带前一条的指纹：

```
entry[n].prev_hash = entry[n-1].hash
entry[n].hash     = sha256(canonical_json(entry[n]) + prev_hash)
```

于是存在三种篡改，三种都被覆盖：

| 篡改方式 | 检测手段 |
| --- | --- |
| 改内容但**不重算**哈希 | `hash mismatch` |
| 改内容**并重算**哈希 | 下一条的 `prev_hash` 对不上 → `broken link` |
| **整条删除** | 序号不再连续 → `non-contiguous` |

### 技术选型

| 选择 | 理由 |
| --- | --- |
| 纯标准库 | 零供应链风险、离线可用、`pip install` 秒完成 |
| JSONL 存储 | 追加写天然原子、可用 `tail -f` 观察、易被任何语言解析 |
| JSON 策略 | 无需引入 YAML 解析器即可保持人类可读与机器可校验 |
| `fnmatch` glob | 标准库自带，语义与 shell 一致，学习成本为零 |
| SHA-256 | 广泛可用、无合规争议 |

### 迭代规划

- [ ] 🔁 审计链**回放**（replay）模式：从审计日志重演一次会话
- [ ] 🤝 `ask` 决策的交互式审批后端（TTY / Webhook）
- [ ] 📤 审计链导出为 Sigstore / in-toto 证明格式
- [ ] 🧩 策略模板市场（`--template ci-strict`）
- [ ] 🐳 可选的容器级隔离后端（当前为文件系统级）
- [ ] 📈 审计指标 Prometheus 导出

社区贡献方向：新增动作类型、补充高危命令模式、翻译更多语言文档。

---

## 📦 打包与部署指南

本项目属于 **CLI 工具 / Python 库**，无需上传各平台二进制；源码包与 wheel 均为**纯 Python、跨平台通用**（`py3-none-any`）。

### 一键构建

```bash
# macOS / Linux
./scripts/build.sh          # 产出 dist/*.tar.gz 与 dist/*.whl
./scripts/build.sh test     # 只跑测试
./scripts/build.sh clean    # 清理构建产物

# Windows
scripts\build.bat
scripts\build.bat test
scripts\build.bat clean
```

### 标准 PEP 517 构建

```bash
python -m pip install build
python -m build --sdist --wheel
```

### 从源码安装 / 开发模式

```bash
pip install .            # 正常安装，获得 cubicle 命令
pip install -e .         # 可编辑模式，改代码即时生效
```

### 部署到服务器

```bash
pip install agentcubicle-1.0.0-py3-none-any.whl
cubicle --base /var/lib/agentcubicle init prod-agent
cubicle --base /var/lib/agentcubicle policy prod-agent > /etc/agentcubicle-policy.json
```

建议把 `--base` 指向持久化目录，并定期执行 `cubicle audit <name> --verify` 纳入巡检。

### 测试

```bash
python tests/run_tests.py        # 零依赖，无需 pytest
python -m unittest discover -s tests
```

### 兼容环境

| 环境 | 状态 |
| --- | --- |
| Python 3.8 / 3.9 / 3.10 / 3.11 / 3.12 | ✅ 支持 |
| Windows 10+ / macOS 12+ / Linux | ✅ 支持 |
| 无网络环境 | ✅ 完全离线可用 |
| 只读 HOME 目录 | ⚠️ 请用 `--base` 指定可写目录 |

---

## 🤝 贡献指南

欢迎 PR 与 Issue！

**提交规范**（Angular 风格）

- `feat: 新增 xxx 功能`
- `fix: 修复 xxx 问题`
- `docs: 更新 xxx 文档`
- `refactor: 重构 xxx 模块`
- `test: 补充 xxx 用例`
- `chore: 构建/工具链调整`

**PR 流程**

1. Fork 本仓库并新建分支（`feat/xxx`）；
2. 保持**零第三方依赖**这一底线（测试依赖除外）；
3. 为新增逻辑补充单元测试，确保 `python tests/run_tests.py` 全绿；
4. 更新相关语言版本的 README；
5. 提交 PR 并描述改动动机与自测结果。

**Issue 反馈**：请附上 Python 版本、操作系统、复现命令与完整输出。发现安全问题时，请先通过 Issue 隐去敏感路径后再描述。

---

## 📄 开源协议

本项目基于 **[MIT License](LICENSE)** 开源。

- ✅ 允许商业使用、修改、分发、私有化部署
- ✅ 允许用于闭源产品
- ⚠️ 需保留版权声明与许可声明
- ❌ 作者不承担任何担保与使用风险

> 安全提示：AgentCubicle 提供的是**文件系统级**隔离与审计能力，不等同于操作系统级沙箱或容器。处理不可信代码时，请在其外再叠加容器 / 虚拟机等更强的隔离层。

---

<div align="center">

如果这个项目对你有帮助，欢迎点个 ⭐ Star 支持一下！

Made with 🛡️ by [gitstq](https://github.com/gitstq)

</div>
