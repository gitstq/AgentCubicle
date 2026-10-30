<div align="center">

# 🛡️ AgentCubicle

**AI エージェントのための防音ワークスペース —— まず裁決、そして実行、すべて記録。**

[简体中文](README.md) · [繁體中文](README.zh-TW.md) · [English](README.en.md) · [日本語](README.ja.md)

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)
![Dependencies](https://img.shields.io/badge/dependencies-zero-2ea44f)
![License](https://img.shields.io/badge/license-MIT-yellow)
![Offline](https://img.shields.io/badge/offline-first-blue)
![Tests](https://img.shields.io/badge/tests-83%20passing-brightgreen)
![Platform](https://img.shields.io/badge/platform-Win%20%7C%20macOS%20%7C%20Linux-lightgrey)

[📦 リリースダウンロード](https://github.com/gitstq/AgentCubicle/releases/latest)

</div>

---

## 🎉 プロジェクト紹介

エージェントが「自分専用のコンピュータ」を手に入れた瞬間から、本当の問題が始まります。**どのファイルを変更し、どのコマンドを実行し、どのサイトに接続したのか**——そして問題が起きたとき、そのログは証拠として信頼できるでしょうか。

AgentCubicle は、もうひとつのエージェントフレームワークではありません。**エージェントと現実世界のあいだに立つ水門**です。

- 🧊 **Cubicle（ワークスペース）**：エージェントごとに独立した隔離ディレクトリを割り当て、読み書き範囲をその中に固定します。
- 🛡️ **事前裁決**：いかなる操作も、実行前に必ずポリシーエンジンの判定（`allow` / `deny` / `ask`）を通ります。しかも**根拠となる理由と該当ルール**まで返します。
- ⛓️ **改ざん検知監査**：すべてのレコードを SHA-256 ハッシュチェーンで連結。1 件書き換えれば以降すべてが破綻し、検証は一瞬です。

**解決する課題**

| 課題 | 従来の対処 | AgentCubicle |
| --- | --- | --- |
| エージェントがホストのファイルを誤削除・誤変更 | プロンプトに「触らないで」と書く | パス許可リスト + エスケープ検出で**強制ブロック** |
| 事後に経緯を再現できない | stdout ログを漁る | ハッシュチェーン監査で検証・リプレイ可能 |
| ログ自体が改ざんされる | 打つ手なし | 改ざんは即断链。`audit --verify` が数秒で検出 |
| 無限ループ・ディスク大量書き込み | 事後に請求書を見る | 回数／バイト数／実行時間の**三重バジェット** |
| セキュリティツールが大量の依存を持ち込む | `pip install` で祈る | **サードパーティ依存ゼロ**、標準ライブラリのみ |

**自社開発ならではの強み**

- 🪶 **真のゼロ依存**：Python 標準ライブラリのみ。完全オフラインで動作し、ネットワークパケットを 1 つも送りません。
- ⛓️ **単なるログではなくハッシュチェーン**：本プロジェクト最大の独自性です。監査とは「書き残す」ことではなく、**暗号学的に検証可能な追記専用チェーン**であるべきだという発想に基づきます。ハッシュを再計算する巧妙な改ざんも、リンク検証で必ず露見します。
- 🧠 **説明可能な裁決**：`reason` + `rule` + `risk` を返すため、単なる真偽値ではなく、そのまま LLM にフィードバックして自己修正させられます。
- 🧪 **ドライラン事前検査**：`check` / `dry_run()` で副作用ゼロの一括判定。
- 🚫 **多層防御**：ポリシーの deny リストに加え、「シェルへのパイプ」「コマンド置換」「ブロックデバイスへの書き込み」「fork 爆弾」などの危険パターンを**ポリシーとは別に**内蔵。設定漏れでも必ず止めます。

**着想元**：GitHub Trending の `OpenMausBot`（各 bot が自分のコンピュータを持ち、操作は事前裁決・事後記録される）および `t3code`（エージェント制御面）のプロダクト思想。いずれも重量級の Electron／デスクトップ構成でクラウド前提ですが、AgentCubicle は同じ安全モデルを**依存ゼロのターミナル CLI に凝縮**しました。コードは 100% 自社開発で、両者の実装は一切再利用していません。

---

## ✨ 主な特徴

- 🧊 **隔離ワークスペース**：`init` するだけで `workspace/`、`tmp/`、`output/`、`audit/` の 4 点セットが揃います。
- 🛡️ **ポリシー駆動の事前裁決**：`file.read` / `file.write` / `file.delete` / `shell.exec` / `net.fetch` の 5 種類に対応。
- 🚦 **3 状態の判定**：`allow`（許可）／`deny`（拒否）／`ask`（人手確認）。いずれも理由と該当ルール付き。
- ⛓️ **改ざん検知チェーン**：`prev_hash + sha256`。`audit --verify` が「何件目のどのハッシュが不一致か」まで特定します。
- 🧱 **パスエスケープ防御**：`../../`・絶対パス・シンボリックリンク経由の脱出をすべて拒否。ルールは正規化された **posix 相対パス**で照合するため、プラットフォーム間で挙動が一致します。
- 💣 **危険コマンドのガード**：`curl x | sh`、`` `cmd` ``、`$(...)`、`> /dev/sda`、`rm -rf /`、fork 爆弾を**ポリシーとは独立に**ブロック。
- 📊 **三重バジェット**：アクション回数・書き込みバイト数・実行時間。超過すれば即拒否。
- 🧾 **3 形式のレポート**：`text` / `markdown` / `json`。CI 成果物にも目視レビューにも最適。
- 🧪 **副作用ゼロの事前検査**：`cubicle check` と `Guard.dry_run()`。
- 🔌 **CLI とライブラリの両対応**：`cubicle run demo -- ls` でも、`from agentcubicle import Guard` でも使えます。
- 🖥️ **クロスプラットフォーム**：Windows / macOS / Linux、Python 3.8 以上。
- 🧩 **子プロセス環境の洗浄**：`PATH`/`HOME` など最小限の変数だけを継承し、ホストの資格情報を漏らしません。

---

## 🚀 クイックスタート

### 動作要件

| 項目 | 要件 |
| --- | --- |
| Python | **3.8 以上**（3.11 / 3.12 で検証済み） |
| サードパーティ依存 | **なし** |
| OS | Windows / macOS / Linux |
| ディスク | 1 キュービクルあたり数 KB（成果物を除く） |

### インストール

**方法 1：ソースから（推奨。ビルドツール不要）**

```bash
git clone https://github.com/gitstq/AgentCubicle.git
cd AgentCubicle
python -m agentcubicle --version     # インストール不要でそのまま実行可
```

**方法 2：pip（`cubicle` コマンドが使えます）**

```bash
git clone https://github.com/gitstq/AgentCubicle.git
cd AgentCubicle
pip install .
cubicle --version
```

**方法 3：リリースのホイールから**

```bash
pip install https://github.com/gitstq/AgentCubicle/releases/latest/download/agentcubicle-1.0.0-py3-none-any.whl
```

### 60 秒で体験

```bash
# 1️⃣ ワークスペースを作る
cubicle init demo

# 2️⃣ 実行前に問い合わせる（副作用なし）
cubicle check demo file.write workspace/notes.txt
# ✅ ALLOW  file.write  workspace/notes.txt

# 3️⃣ 実際に書き込む
cubicle write demo workspace/notes.txt --data "hello agent"

# 4️⃣ ワークスペース内でコマンド実行
cubicle run demo -- echo hello

# 5️⃣ 境界を越えようとする（ブロックされます）
cubicle check demo file.write ../../.bashrc
# ⛔ DENY  path escapes the workspace root

# 6️⃣ 監査チェーンが改ざんされていないか検証
cubicle audit demo --verify
# ✅ audit chain intact — no tampering detected
```

### ライブラリとして使う

```python
from agentcubicle import Cubicle, Guard

cubicle = Cubicle("demo")
if not cubicle.exists:
    cubicle.create()

guard = Guard(cubicle, actor="my-agent", session="s-001")

result = guard.write_file("workspace/report.txt", b"hello")
print(result.decision.effect)   # allow / deny / ask
print(result.decision.reason)   # 根拠となる理由
print(result.decision.rule)     # 該当したポリシールール

# 一括事前検査：判定のみで実行しません
for d in guard.dry_run([("file.write", "workspace/a.txt"),
                        ("file.write", ".env")]):
    print(d.effect, d.reason)
```

---

## 📖 詳細な使い方

### コマンド一覧

| コマンド | 用途 |
| --- | --- |
| `cubicle init <name>` | 隔離ワークスペースを作成 |
| `cubicle list` | 全ワークスペースを一覧表示 |
| `cubicle info <name>` | 詳細（ポリシー、監査件数、チェーン状態）を表示 |
| `cubicle rm <name> --yes` | ワークスペースを削除 |
| `cubicle check <name> <action> <target...>` | **事前裁決**（副作用なし） |
| `cubicle run <name> -- <command>` | ポリシー配下でコマンド実行 |
| `cubicle write <name> <path> --data <text>` | 制御付き書き込み（`--data` 省略で標準入力） |
| `cubicle read <name> <path>` | 制御付き読み取り |
| `cubicle audit <name> [--tail N] [--verify]` | チェーンの閲覧／検証 |
| `cubicle report <name> [--format text\|markdown\|json]` | 監査レポート生成 |
| `cubicle policy <name>` | 現在のポリシーを表示 |

グローバルオプション：`--base <dir>`（既定の `~/.agentcubicle` を上書き。**サブコマンドの前後どちらでも指定可**）、`--version`。

### 5 種類のアクション

| action | 意味 | target の例 |
| --- | --- | --- |
| `file.read` | ファイル読み取り | `workspace/a.txt` |
| `file.write` | ファイル書き込み | `output/report.json` |
| `file.delete` | ファイル削除 | `tmp/cache.bin` |
| `shell.exec` | コマンド実行 | `git status` |
| `net.fetch` | ネットワークアクセス | `https://api.github.com` |

### ディレクトリ構成

```
~/.agentcubicle/cubicles/<name>/
├── policy.json          # ポリシー（直接編集可能）
├── cubicle.json         # メタ情報
├── workspace/           # エージェントの主作業領域（既定で書き込み可）
├── tmp/                 # 一時領域（既定で書き込み可）
├── output/              # 成果物領域（既定で書き込み可）
└── audit/audit.jsonl    # ハッシュチェーン監査ログ
```

> ⚠️ **パスの基準**：すべての相対パスは `workspace/` ではなく **cubicle ルート**（上の `<name>/`）が基準です。したがって `workspace/notes.txt` はディスク上では `<name>/workspace/notes.txt` になります。

### ポリシー設定

`cubicle init` 後に `policy.json` を編集してください。完全な構造（既定値）：

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

| フィールド | 説明 |
| --- | --- |
| `default_effect` | どのルールにもマッチしない場合の既定値。既定は保守的な `ask`。`deny` にすると最も厳しい許可リスト方式になります |
| `paths.*` | glob ルール。`docs` と書けば `docs/**` と同等で、配下すべてをカバーします |
| `commands.allow/deny` | コマンドの glob。`deny` を先に評価し、常に `deny` が優先されます |
| `network.allow_hosts/deny_hosts` | ホスト名の glob。大文字小文字・ポート・パスは自動的に無視されます |
| `budgets.*` | 三重バジェット。`0` は無制限を意味します |

> 🔐 **マージの意味**：ユーザーポリシーは内蔵の既定ポリシーに**深くマージ**されますが、**リスト項目は追記ではなく置換**です。セキュリティツールとしてのフェイルセーフ設計であり、許可リストを絞り込めば確実に反映されます。

ポリシーファイル単体を検証する：

```bash
cubicle policy --policy-file ./my-policy.json
```

### 活用レシピ

**CI 内のエージェントを厳格に制限する**

```json
{
  "default_effect": "deny",
  "paths": { "write_allow": ["output/**"] },
  "commands": { "allow": ["python -m pytest*"] },
  "network": { "deny_hosts": ["*"] },
  "budgets": { "max_actions": 30 }
}
```

**特定の API のみ許可する**

```json
{ "network": { "allow_hosts": ["api.github.com", "*.openai.com"], "deny_hosts": [] } }
```

**裁決結果を LLM に戻して自己修正させる**

```python
result = guard.write_file("workspace/x.txt", b"data")
if not result.decision.allowed:
    prompt_hint = f"Action denied: {result.decision.reason} (rule={result.decision.rule})"
```

**CI で監査レポートを保存する**

```bash
cubicle report demo --format markdown --output audit-report.md
cubicle audit demo --verify || exit 1      # チェーン断絶でパイプライン失敗
```

### 終了コード

| コード | 意味 |
| --- | --- |
| `0` | 成功／許可 |
| `1` | 実行時エラー（ワークスペース不在、チェーン断絶など） |
| `3` | **ポリシーにより拒否** |
| 子プロセスの終了コード | `cubicle run` は実行したコマンドの終了コードをそのまま返します |

---

## 💡 設計思想とロードマップ

### 設計哲学

1. **拒否も記録に残す**。ブロックされた操作も監査チェーンに書き込まれます。「誰がいつ境界を越えようとしたか」は、「何が成功したか」より価値が高いことが多いからです。
2. **実行より説明を優先**。単なる真偽値ではなく `reason + rule + risk` を返すことで、エージェントは壁にぶつかるのではなく境界を理解して自己修正できます。
3. **既定は保守的**。読み取りは自由、書き込みは限定、ネットワークは禁止、`default_effect` は `ask`。緩めるなら明示的に。
4. **多層防御**。パス正規化・エスケープ検出・危険パターン・環境洗浄の 4 層を重ね、「ユーザーがポリシーを正しく書いている」ことに依存しません。
5. **ゼロ依存はセキュリティ属性である**。依存が少なければサプライチェーン攻撃面は小さく、監査コストも下がります。

### なぜ通常のログではなくハッシュチェーンなのか

通常の JSONL ログは 1 行書き換えられても誰も気づきません。ハッシュチェーンは各レコードに 1 つ前の指紋を保持させます。

```
entry[n].prev_hash = entry[n-1].hash
entry[n].hash     = sha256(canonical_json(entry[n]) + prev_hash)
```

改ざん手法は 3 通り、検出も 3 通り：

| 改ざん手法 | 検出 |
| --- | --- |
| 内容を変更し**ハッシュを再計算しない** | `hash mismatch` |
| 内容を変更し**ハッシュも再計算した** | 次のレコードの `prev_hash` が不一致 → `broken link` |
| **レコードごと削除** | 連番が途切れる → `non-contiguous` |

### 技術選定

| 選択 | 理由 |
| --- | --- |
| 標準ライブラリのみ | サプライチェーンリスクゼロ、オフライン可、インストールは一瞬 |
| JSONL 保存 | 追記が原子的、`tail -f` で観察可、どの言語でも解析容易 |
| JSON ポリシー | YAML パーサなしで人間可読かつ機械検証可能 |
| `fnmatch` glob | 標準搭載、シェルと同じ感覚で学習コストゼロ |
| SHA-256 | 広く利用可能でコンプライアンス上の懸念がない |

### ロードマップ

- [ ] 🔁 監査チェーンの**リプレイ**機能
- [ ] 🤝 `ask` 判定の対話的承認バックエンド（TTY / Webhook）
- [ ] 📤 Sigstore / in-toto 形式でのチェーン書き出し
- [ ] 🧩 ポリシーテンプレート集（`--template ci-strict`）
- [ ] 🐳 コンテナレベルの隔離バックエンド（現在はファイルシステムレベル）
- [ ] 📈 監査指標の Prometheus エクスポート

コントリビュート歓迎：新しいアクション種別、危険コマンドパターンの追加、ドキュメントの多言語化。

---

## 📦 パッケージングとデプロイ

本プロジェクトは **CLI ツール／Python ライブラリ**であり、プラットフォーム別バイナリは不要です。ソース配布物もホイールも**純粋な Python でクロスプラットフォーム**（`py3-none-any`）です。

### ワンコマンドビルド

```bash
# macOS / Linux
./scripts/build.sh          # dist/*.tar.gz と dist/*.whl を生成
./scripts/build.sh test     # テストのみ
./scripts/build.sh clean    # ビルド成果物を削除

# Windows
scripts\build.bat
scripts\build.bat test
scripts\build.bat clean
```

### 標準的な PEP 517 ビルド

```bash
python -m pip install build
python -m build --sdist --wheel
```

### ソースからインストール／編集可能インストール

```bash
pip install .            # 通常インストール（`cubicle` コマンドが使えます）
pip install -e .         # 編集可能モード、変更が即反映
```

### サーバへのデプロイ

```bash
pip install agentcubicle-1.0.0-py3-none-any.whl
cubicle --base /var/lib/agentcubicle init prod-agent
cubicle --base /var/lib/agentcubicle policy prod-agent > /etc/agentcubicle-policy.json
```

`--base` は永続化ディレクトリを指定し、`cubicle audit <name> --verify` を定期監視に組み込むことを推奨します。

### テスト

```bash
python tests/run_tests.py        # 依存ゼロ。pytest 不要
python -m unittest discover -s tests
```

### 対応環境

| 環境 | 状態 |
| --- | --- |
| Python 3.8 / 3.9 / 3.10 / 3.11 / 3.12 | ✅ 対応 |
| Windows 10+ / macOS 12+ / Linux | ✅ 対応 |
| ネットワーク遮断環境 | ✅ 完全オフライン動作 |
| `$HOME` が読み取り専用 | ⚠️ 書き込み可能な `--base` を指定してください |

---

## 🤝 コントリビューションガイド

PR と Issue を歓迎します。

**コミット規約**（Angular スタイル）

- `feat: 新機能 xxx を追加`
- `fix: xxx の問題を修正`
- `docs: xxx のドキュメントを更新`
- `refactor: xxx モジュールをリファクタリング`
- `test: xxx のテストを追加`
- `chore: ビルド／ツールチェーンの調整`

**PR の流れ**

1. リポジトリをフォークし、ブランチを作成（`feat/xxx`）。
2. **サードパーティ依存ゼロ**の原則を守る（テスト用依存は除く）。
3. 新規ロジックにはユニットテストを追加し、`python tests/run_tests.py` が全て通ることを確認。
4. 関連する言語版の README も更新する。
5. PR に変更の動機とテスト結果を記載する。

**Issue 報告**：Python バージョン、OS、再現コマンド、完全な出力を添えてください。セキュリティ関連の場合は、機微なパスを伏せてからご報告ください。

---

## 📄 ライセンス

本プロジェクトは **[MIT License](LICENSE)** の下で公開されています。

- ✅ 商用利用、改変、再配布、プライベート展開が可能
- ✅ クローズドソース製品への組み込みが可能
- ⚠️ 著作権表示とライセンス表示の保持が必要
- ❌ 作者は一切の保証と責任を負いません

> セキュリティ上の注意：AgentCubicle が提供するのは**ファイルシステムレベル**の隔離と監査であり、OS レベルのサンドボックスやコンテナとは異なります。信頼できないコードを扱う場合は、コンテナや仮想マシンによる隔離を併用してください。

---

<div align="center">

このプロジェクトが役に立ったら、⭐ を押していただけると励みになります！

Made with 🛡️ by [gitstq](https://github.com/gitstq)

</div>
