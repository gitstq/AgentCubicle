<div align="center">

# 🛡️ AgentCubicle

**給 AI Agent 的一間隔音工位：先裁決，再動手，全程留痕。**

[简体中文](README.md) · [繁體中文](README.zh-TW.md) · [English](README.en.md) · [日本語](README.ja.md)

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)
![Dependencies](https://img.shields.io/badge/dependencies-zero-2ea44f)
![License](https://img.shields.io/badge/license-MIT-yellow)
![Offline](https://img.shields.io/badge/offline-first-blue)
![Tests](https://img.shields.io/badge/tests-83%20passing-brightgreen)
![Platform](https://img.shields.io/badge/platform-Win%20%7C%20macOS%20%7C%20Linux-lightgrey)

[📦 Release 下載](https://github.com/gitstq/AgentCubicle/releases/latest)

</div>

---

## 🎉 專案介紹

當 Agent 拿到一台「電腦」之後，真正的問題才剛開始：它**改了哪些檔案、跑了什麼指令、連了哪些網站**？出事之後，紀錄能不能當成證據？

AgentCubicle 就是為這個問題而生的。它不是又一套 Agent 框架，而是**架在 Agent 與真實世界之間的那道閘門**：

- 🧊 **Cubicle（工位）**：每個 Agent 領到一個獨立的隔離目錄，讀寫範圍被釘死在裡面；
- 🛡️ **前置裁決**：任何動作在執行前都必須先過政策引擎，得到 `allow` / `deny` / `ask`，並附上**可解釋的理由與命中的規則**；
- ⛓️ **防竄改稽核**：每筆紀錄都串在 SHA-256 雜湊鏈上，改一筆，後面全斷，一驗便知。

**解決的核心痛點**

| 痛點 | 傳統做法 | AgentCubicle |
| --- | --- | --- |
| Agent 誤刪／誤改宿主檔案 | 靠 prompt 裡寫「不要亂動」 | 路徑白名單 + 逃逸偵測，**硬擋** |
| 出事後無法還原經過 | 翻 stdout 紀錄 | 雜湊鏈稽核，可驗證、可回放 |
| 紀錄本身可被竄改 | 無解 | 竄改即斷鏈，`audit --verify` 秒級發現 |
| Agent 無限呼叫／狂寫磁碟 | 事後看帳單 | 動作數／位元組數／執行時間**三重預算** |
| 引入安全工具反而帶來一堆相依 | `pip install` 一堆套件 | **零第三方相依**，純標準函式庫 |

**自研差異化亮點**

- 🪶 **真·零相依**：只用 Python 標準函式庫，對環境純度有潔癖的人也能安心用；完全離線，一個網路封包都不發。
- ⛓️ **雜湊鏈而非一般紀錄**：這是本專案的核心原創點。稽核不是「記錄一下」，而是**密碼學上可驗證的僅附加鏈**，任何事後修改（就算重算雜湊）都會被斷鏈偵測抓到。
- 🧠 **可解釋裁決**：每次裁決都回傳 `reason` + `rule` + `risk`，不是黑箱 `True/False`，方便直接餵回 LLM 做自我修正。
- 🧪 **Dry-run 預檢**：動真格之前先 `check` / `dry_run` 批次試算裁決，零副作用。
- 🚫 **縱深防禦**：除了政策 deny 清單，還內建一組「管線進 shell／指令替換／寫入區塊裝置／fork bomb」高危模式，**即使政策寫漏了也能兜底**。

**靈感來源**：GitHub Trending 上的 `OpenMausBot`（每個 bot 擁有自己的電腦、動作先決策後記錄）與 `t3code`（Agent 控制面）的產品思路。兩者都是重量級的 Electron／桌面堆疊且依賴雲端服務，AgentCubicle 則把同樣的安全模型**濃縮成一個零相依的終端機 CLI**——程式碼 100% 自研，未複用其任何實作。

---

## ✨ 核心特性

- 🧊 **隔離工位**：`init` 一個 cubicle 就得到 `workspace/`、`tmp/`、`output/`、`audit/` 四件套，Agent 的活動半徑一目了然。
- 🛡️ **政策前置裁決**：`file.read` / `file.write` / `file.delete` / `shell.exec` / `net.fetch` 五類動作全覆蓋。
- 🚦 **三態決策**：`allow`（放行）／`deny`（拒絕）／`ask`（需人工確認），每筆都帶理由與命中規則。
- ⛓️ **防竄改稽核鏈**：`prev_hash + sha256`，`audit --verify` 一鍵驗真，精確到「第幾筆、哪個雜湊對不上」。
- 🧱 **路徑逃逸防護**：`../../`、絕對路徑、符號連結逃逸一律拒絕，政策規則在正規化後的 **posix 相對路徑**上比對，跨平台行為一致。
- 💣 **危險指令兜底**：`curl x | sh`、`` `cmd` ``、`$(...)`、`> /dev/sda`、`rm -rf /`、fork bomb 等模式**在政策之外**額外攔截。
- 📊 **三重預算**：動作次數、寫入位元組數、執行時間，超限即拒，杜絕失控迴圈。
- 🧾 **多格式報告**：`text` / `markdown` / `json` 三種稽核報告，可直接丟進 CI 產物或人工複核。
- 🧪 **零副作用預檢**：`cubicle check` 與 `Guard.dry_run()` 只裁決不執行。
- 🔌 **CLI + 函式庫雙形態**：既能 `cubicle run demo -- ls`，也能 `from agentcubicle import Guard` 嵌進你自己的 Agent 迴圈。
- 🖥️ **跨平台**：Windows / macOS / Linux 通吃，Python 3.8 起。
- 🧩 **環境清洗**：子行程只繼承 `PATH`/`HOME` 等必要變數，宿主憑證不會外洩給 Agent。

---

## 🚀 快速開始

### 環境需求

| 項目 | 需求 |
| --- | --- |
| Python | **3.8 以上**（3.11 / 3.12 已實測） |
| 第三方相依 | **無** |
| 作業系統 | Windows / macOS / Linux |
| 磁碟 | 每個 cubicle 約幾 KB（不含你的產出） |

### 安裝

**方式一：從原始碼（推薦，零建置工具相依）**

```bash
git clone https://github.com/gitstq/AgentCubicle.git
cd AgentCubicle
python -m agentcubicle --version     # 免安裝即可直接使用
```

**方式二：pip 安裝（含 `cubicle` 指令）**

```bash
git clone https://github.com/gitstq/AgentCubicle.git
cd AgentCubicle
pip install .
cubicle --version
```

**方式三：從 Release 附件安裝**

```bash
pip install https://github.com/gitstq/AgentCubicle/releases/latest/download/agentcubicle-1.0.0-py3-none-any.whl
```

### 60 秒上手

```bash
# 1️⃣ 建一個工位
cubicle init demo

# 2️⃣ 動手前先問一句（零副作用）
cubicle check demo file.write workspace/notes.txt
# ✅ ALLOW  file.write  workspace/notes.txt

# 3️⃣ 真正寫入
cubicle write demo workspace/notes.txt --data "hello agent"

# 4️⃣ 在工位裡執行指令
cubicle run demo -- echo hello

# 5️⃣ 試試越界（會被硬擋）
cubicle check demo file.write ../../.bashrc
# ⛔ DENY  path escapes the workspace root

# 6️⃣ 驗證稽核鏈有沒有被動過手腳
cubicle audit demo --verify
# ✅ audit chain intact — no tampering detected
```

### 作為 Python 函式庫使用

```python
from agentcubicle import Cubicle, Guard

cubicle = Cubicle("demo")
if not cubicle.exists:
    cubicle.create()

guard = Guard(cubicle, actor="my-agent", session="s-001")

result = guard.write_file("workspace/report.txt", b"hello")
print(result.decision.effect)   # allow / deny / ask
print(result.decision.reason)   # 可解釋理由
print(result.decision.rule)     # 命中的政策規則

# 批次預檢：只裁決，不執行
for d in guard.dry_run([("file.write", "workspace/a.txt"),
                        ("file.write", ".env")]):
    print(d.effect, d.reason)
```

---

## 📖 詳細使用指南

### 指令總覽

| 指令 | 用途 |
| --- | --- |
| `cubicle init <name>` | 建立隔離工位 |
| `cubicle list` | 列出所有工位 |
| `cubicle info <name>` | 查看工位詳情（政策、稽核筆數、鏈狀態） |
| `cubicle rm <name> --yes` | 刪除工位 |
| `cubicle check <name> <action> <target...>` | **事前裁決**，零副作用 |
| `cubicle run <name> -- <command>` | 受政策約束地執行指令 |
| `cubicle write <name> <path> --data <text>` | 受控寫檔（`--data` 省略則讀 stdin） |
| `cubicle read <name> <path>` | 受控讀檔 |
| `cubicle audit <name> [--tail N] [--verify]` | 查看／驗證稽核鏈 |
| `cubicle report <name> [--format text\|markdown\|json]` | 產生稽核報告 |
| `cubicle policy <name>` | 查看目前政策 |

全域參數：`--base <dir>`（覆寫預設的 `~/.agentcubicle` 根目錄，**子指令前後皆可使用**）、`--version`。

### 五類動作

| action | 意義 | target 範例 |
| --- | --- | --- |
| `file.read` | 讀取檔案 | `workspace/a.txt` |
| `file.write` | 寫入檔案 | `output/report.json` |
| `file.delete` | 刪除檔案 | `tmp/cache.bin` |
| `shell.exec` | 執行指令 | `git status` |
| `net.fetch` | 網路存取 | `https://api.github.com` |

### 工位目錄結構

```
~/.agentcubicle/cubicles/<name>/
├── policy.json          # 政策文件（可直接編輯）
├── cubicle.json         # 中繼資訊
├── workspace/           # Agent 主戰場（預設可寫）
├── tmp/                 # 暫存目錄（預設可寫）
├── output/              # 產出目錄（預設可寫）
└── audit/audit.jsonl    # 雜湊鏈稽核紀錄
```

> ⚠️ **路徑基準**：所有相對路徑都以 **cubicle 根目錄**（上圖的 `<name>/`）為基準，而不是 `workspace/`。因此 `workspace/notes.txt` 落到磁碟就是 `<name>/workspace/notes.txt`。

### 政策設定

`cubicle init` 之後編輯 `policy.json` 即可。完整結構（預設值）：

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

**欄位說明**

| 欄位 | 說明 |
| --- | --- |
| `default_effect` | 沒有任何規則命中時的兜底取值，建議 `ask`（保守）；設 `deny` 則變成最嚴格的白名單模式 |
| `paths.*` | glob 規則。**寫 `docs` 等同於 `docs/**`**，會自動覆蓋其下所有內容 |
| `commands.allow/deny` | 指令 glob，先比對 deny 再比對 allow；deny 優先 |
| `network.allow_hosts/deny_hosts` | 主機名稱 glob，自動忽略大小寫、埠號與路徑 |
| `budgets.*` | 三重預算，`0` 表示不限制 |

> 🔐 **合併語意**：你的政策會**深度合併**到內建預設政策之上，且**清單欄位是覆寫而非附加**——這是安全工具的 fail-safe 取向，收窄白名單一定生效。

驗證一份政策文件是否合法：

```bash
cubicle policy --policy-file ./my-policy.json
```

### 典型情境

**情境一：給 CI 裡的 Agent 上枷鎖（最嚴格白名單）**

```json
{
  "default_effect": "deny",
  "paths": { "write_allow": ["output/**"] },
  "commands": { "allow": ["python -m pytest*"] },
  "network": { "deny_hosts": ["*"] },
  "budgets": { "max_actions": 30 }
}
```

**情境二：允許存取特定 API**

```json
{ "network": { "allow_hosts": ["api.github.com", "*.openai.com"], "deny_hosts": [] } }
```

**情境三：把裁決結果餵回 LLM 自我修正**

```python
result = guard.write_file("workspace/x.txt", b"data")
if not result.decision.allowed:
    prompt_hint = f"Action denied: {result.decision.reason} (rule={result.decision.rule})"
```

**情境四：CI 歸檔稽核報告**

```bash
cubicle report demo --format markdown --output audit-report.md
cubicle audit demo --verify || exit 1      # 鏈斷了直接讓 pipeline 失敗
```

### 結束碼

| 結束碼 | 意義 |
| --- | --- |
| `0` | 成功／允許 |
| `1` | 執行錯誤（工位不存在、稽核鏈斷裂等） |
| `3` | **動作被政策拒絕** |
| 子行程結束碼 | `cubicle run` 會透傳被執行指令的結束碼 |

---

## 💡 設計思路與迭代規劃

### 設計哲學

1. **拒絕也要留痕**。被擋下的動作同樣寫入稽核鏈——「誰在什麼時候試圖越界」往往比「誰做了什麼」更有價值。
2. **可解釋優先於可執行**。回傳 `reason + rule + risk` 而不是一個布林值，讓 Agent 有能力理解邊界並自我修正，而不只是一頭撞牆。
3. **預設保守**。預設政策允許自由讀取、限制寫入範圍、停用網路；`default_effect` 預設 `ask`。想放寬，請明確宣告。
4. **縱深防禦**。不把安全寄託在「使用者政策寫得對」上：路徑正規化 + 逃逸偵測 + 高危模式兜底 + 環境清洗，四層疊加。
5. **零相依是一種安全屬性**。相依越少，供應鏈攻擊面越小，稽核成本越低。

### 為什麼用雜湊鏈而不是一般紀錄

一般的 JSONL 紀錄被改一行，沒人看得出來。雜湊鏈讓每筆紀錄攜帶前一筆的指紋：

```
entry[n].prev_hash = entry[n-1].hash
entry[n].hash     = sha256(canonical_json(entry[n]) + prev_hash)
```

於是存在三種竄改，三種都被涵蓋：

| 竄改方式 | 偵測手段 |
| --- | --- |
| 改內容但**不重算**雜湊 | `hash mismatch` |
| 改內容**並重算**雜湊 | 下一筆的 `prev_hash` 對不上 → `broken link` |
| **整筆刪除** | 序號不再連續 → `non-contiguous` |

### 技術選型

| 選擇 | 理由 |
| --- | --- |
| 純標準函式庫 | 零供應鏈風險、離線可用、`pip install` 秒完成 |
| JSONL 儲存 | 附加寫入天然原子、可用 `tail -f` 觀察、易被任何語言解析 |
| JSON 政策 | 無需引入 YAML 解析器即可維持人類可讀與機器可驗證 |
| `fnmatch` glob | 標準函式庫內建，語意與 shell 一致，學習成本為零 |
| SHA-256 | 廣泛可用、無合規爭議 |

### 迭代規劃

- [ ] 🔁 稽核鏈**回放**（replay）模式：從稽核紀錄重演一次工作階段
- [ ] 🤝 `ask` 決策的互動式核准後端（TTY / Webhook）
- [ ] 📤 稽核鏈匯出為 Sigstore / in-toto 證明格式
- [ ] 🧩 政策樣板市集（`--template ci-strict`）
- [ ] 🐳 選用的容器級隔離後端（目前為檔案系統層級）
- [ ] 📈 稽核指標 Prometheus 匯出

社群貢獻方向：新增動作類型、補充高危指令模式、翻譯更多語言文件。

---

## 📦 打包與部署指南

本專案屬於 **CLI 工具／Python 函式庫**，無需上傳各平台二進位檔；原始碼套件與 wheel 皆為**純 Python、跨平台通用**（`py3-none-any`）。

### 一鍵建置

```bash
# macOS / Linux
./scripts/build.sh          # 產出 dist/*.tar.gz 與 dist/*.whl
./scripts/build.sh test     # 只跑測試
./scripts/build.sh clean    # 清除建置產物

# Windows
scripts\build.bat
scripts\build.bat test
scripts\build.bat clean
```

### 標準 PEP 517 建置

```bash
python -m pip install build
python -m build --sdist --wheel
```

### 從原始碼安裝／開發模式

```bash
pip install .            # 一般安裝，取得 cubicle 指令
pip install -e .         # 可編輯模式，改程式碼即時生效
```

### 部署到伺服器

```bash
pip install agentcubicle-1.0.0-py3-none-any.whl
cubicle --base /var/lib/agentcubicle init prod-agent
cubicle --base /var/lib/agentcubicle policy prod-agent > /etc/agentcubicle-policy.json
```

建議把 `--base` 指向持久化目錄，並定期執行 `cubicle audit <name> --verify` 納入巡檢。

### 測試

```bash
python tests/run_tests.py        # 零相依，無需 pytest
python -m unittest discover -s tests
```

### 相容環境

| 環境 | 狀態 |
| --- | --- |
| Python 3.8 / 3.9 / 3.10 / 3.11 / 3.12 | ✅ 支援 |
| Windows 10+ / macOS 12+ / Linux | ✅ 支援 |
| 無網路環境 | ✅ 完全離線可用 |
| 唯讀 HOME 目錄 | ⚠️ 請用 `--base` 指定可寫目錄 |

---

## 🤝 貢獻指南

歡迎 PR 與 Issue！

**提交規範**（Angular 風格）

- `feat: 新增 xxx 功能`
- `fix: 修復 xxx 問題`
- `docs: 更新 xxx 文件`
- `refactor: 重構 xxx 模組`
- `test: 補充 xxx 用例`
- `chore: 建置/工具鏈調整`

**PR 流程**

1. Fork 本專案並開新分支（`feat/xxx`）；
2. 維持**零第三方相依**這條底線（測試相依除外）；
3. 為新增邏輯補上單元測試，確保 `python tests/run_tests.py` 全綠；
4. 更新相關語言版本的 README；
5. 提交 PR 並描述改動動機與自測結果。

**Issue 回報**：請附上 Python 版本、作業系統、重現指令與完整輸出。發現安全問題時，請先透過 Issue 隱去敏感路徑後再描述。

---

## 📄 開源協議

本專案基於 **[MIT License](LICENSE)** 開源。

- ✅ 允許商業使用、修改、散佈、私有化部署
- ✅ 允許用於閉源產品
- ⚠️ 需保留版權聲明與授權聲明
- ❌ 作者不承擔任何擔保與使用風險

> 安全提示：AgentCubicle 提供的是**檔案系統層級**的隔離與稽核能力，不等同於作業系統層級沙箱或容器。處理不可信程式碼時，請在其外再疊加容器／虛擬機等更強的隔離層。

---

<div align="center">

如果這個專案對你有幫助，歡迎點個 ⭐ Star 支持一下！

Made with 🛡️ by [gitstq](https://github.com/gitstq)

</div>
