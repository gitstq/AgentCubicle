<div align="center">

# 🛡️ AgentCubicle

**A soundproof desk for your AI agent: decide first, act second, leave a trail.**

[简体中文](README.md) · [繁體中文](README.zh-TW.md) · [English](README.en.md) · [日本語](README.ja.md)

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)
![Dependencies](https://img.shields.io/badge/dependencies-zero-2ea44f)
![License](https://img.shields.io/badge/license-MIT-yellow)
![Offline](https://img.shields.io/badge/offline-first-blue)
![Tests](https://img.shields.io/badge/tests-83%20passing-brightgreen)
![Platform](https://img.shields.io/badge/platform-Win%20%7C%20macOS%20%7C%20Linux-lightgrey)

[📦 Download Release](https://github.com/gitstq/AgentCubicle/releases/latest)

</div>

---

## 🎉 What is this?

Once an agent gets "a computer of its own", the real questions begin: **which
files did it touch, which commands did it run, which hosts did it call** — and
when something goes wrong, can the log actually be trusted as evidence?

AgentCubicle is not another agent framework. It is **the gate between an agent
and the real world**:

- 🧊 **Cubicle** — every agent gets an isolated directory; its read/write radius
  is nailed down inside it.
- 🛡️ **Pre-action verdict** — nothing executes before the policy engine answers
  `allow` / `deny` / `ask`, together with an **explainable reason and the exact
  rule that fired**.
- ⛓️ **Tamper-evident audit** — records are chained with SHA-256. Edit one entry
  and everything after it breaks; verification takes a second.

**The pain it removes**

| Pain | Usual workaround | AgentCubicle |
| --- | --- | --- |
| Agent deletes or overwrites host files | a polite "please don't" in the prompt | path allow-list + escape detection, **enforced** |
| No way to reconstruct what happened | grep through stdout | hash-chained audit, verifiable and replayable |
| The log itself can be edited | nothing you can do | tampering breaks the chain — `audit --verify` catches it |
| Runaway loops / disk flooding | check the bill afterwards | **three budgets**: actions, bytes, wall-clock |
| The security tool ships 40 dependencies | `pip install` and hope | **zero third-party dependencies**, stdlib only |

**What makes it different**

- 🪶 **Genuinely zero-dependency** — standard library only, fully offline, never
  sends a single packet.
- ⛓️ **A hash chain, not a log file** — the core original idea here. Auditing is
  not "writing things down"; it is a *cryptographically verifiable append-only
  chain*. Even an attacker who recomputes hashes is caught by link verification.
- 🧠 **Explainable verdicts** — every decision carries `reason`, `rule` and
  `risk` instead of a bare boolean, so you can feed it straight back to the LLM
  for self-correction.
- 🧪 **Dry-run pre-checks** — `check` / `dry_run()` evaluate batches with zero
  side effects.
- 🚫 **Defence in depth** — beyond your deny list, a built-in set of high-risk
  patterns (pipe-into-shell, command substitution, writing to block devices,
  fork bombs) catches what a sloppy policy misses.

**Inspiration**: the product thinking behind `OpenMausBot` (every bot gets its
own computer; every action is decided before and recorded after) and `t3code`
(an agent control surface) on GitHub Trending. Both are heavy Electron/desktop
stacks tied to cloud services; AgentCubicle compresses the same safety model
into **a zero-dependency terminal CLI** — 100% independently written, reusing
none of their implementation.

---

## ✨ Features

- 🧊 **Isolated cubicles** — `init` gives you `workspace/`, `tmp/`, `output/`
  and `audit/` in one shot.
- 🛡️ **Policy-driven pre-action verdicts** for all five action types:
  `file.read`, `file.write`, `file.delete`, `shell.exec`, `net.fetch`.
- 🚦 **Three-state decisions** — `allow` / `deny` / `ask`, each with a reason and
  the rule that fired.
- ⛓️ **Tamper-evident chain** — `prev_hash + sha256`; `audit --verify` tells you
  exactly which entry and which hash went wrong.
- 🧱 **Escape-proof paths** — `../../`, absolute paths and symlink escapes are
  rejected; rules match against normalised **posix relative paths** so behaviour
  is identical across platforms.
- 💣 **High-risk command guard** — `curl x | sh`, `` `cmd` ``, `$(...)`,
  `> /dev/sda`, `rm -rf /`, fork bombs blocked *in addition to* your policy.
- 📊 **Three budgets** — action count, bytes written and runtime; over the limit
  means denied.
- 🧾 **Reports in three flavours** — `text`, `markdown` and `json`, ready for CI
  artefacts or human review.
- 🧪 **Zero side-effect pre-checks** — `cubicle check` and `Guard.dry_run()`.
- 🔌 **CLI *and* library** — run `cubicle run demo -- ls`, or embed
  `from agentcubicle import Guard` inside your own agent loop.
- 🖥️ **Cross-platform** — Windows / macOS / Linux, Python 3.8+.
- 🧩 **Sanitised child environment** — only `PATH`/`HOME`-style variables are
  inherited, so host credentials never leak into the agent process.

---

## 🚀 Quick start

### Requirements

| Item | Requirement |
| --- | --- |
| Python | **3.8+** (tested on 3.11 / 3.12) |
| Third-party deps | **none** |
| OS | Windows / macOS / Linux |
| Disk | a few KB per cubicle (excluding your output) |

### Install

**Option 1 — from source (recommended; no build tooling needed)**

```bash
git clone https://github.com/gitstq/AgentCubicle.git
cd AgentCubicle
python -m agentcubicle --version     # usable without installing anything
```

**Option 2 — pip (gives you the `cubicle` command)**

```bash
git clone https://github.com/gitstq/AgentCubicle.git
cd AgentCubicle
pip install .
cubicle --version
```

**Option 3 — from the release wheel**

```bash
pip install https://github.com/gitstq/AgentCubicle/releases/latest/download/agentcubicle-1.0.0-py3-none-any.whl
```

### 60-second tour

```bash
# 1️⃣ Create a desk
cubicle init demo

# 2️⃣ Ask before acting (zero side effects)
cubicle check demo file.write workspace/notes.txt
# ✅ ALLOW  file.write  workspace/notes.txt

# 3️⃣ Actually write
cubicle write demo workspace/notes.txt --data "hello agent"

# 4️⃣ Run a command inside the cubicle
cubicle run demo -- echo hello

# 5️⃣ Try to break out (blocked)
cubicle check demo file.write ../../.bashrc
# ⛔ DENY  path escapes the workspace root

# 6️⃣ Verify nobody tampered with the audit chain
cubicle audit demo --verify
# ✅ audit chain intact — no tampering detected
```

### Use it as a library

```python
from agentcubicle import Cubicle, Guard

cubicle = Cubicle("demo")
if not cubicle.exists:
    cubicle.create()

guard = Guard(cubicle, actor="my-agent", session="s-001")

result = guard.write_file("workspace/report.txt", b"hello")
print(result.decision.effect)   # allow / deny / ask
print(result.decision.reason)   # explainable reason
print(result.decision.rule)     # the rule that fired

# Batch pre-check: verdicts only, nothing executes
for d in guard.dry_run([("file.write", "workspace/a.txt"),
                        ("file.write", ".env")]):
    print(d.effect, d.reason)
```

---

## 📖 Usage guide

### Command reference

| Command | Purpose |
| --- | --- |
| `cubicle init <name>` | create an isolated cubicle |
| `cubicle list` | list all cubicles |
| `cubicle info <name>` | show policy, audit count and chain status |
| `cubicle rm <name> --yes` | delete a cubicle |
| `cubicle check <name> <action> <target...>` | **pre-action verdict**, zero side effects |
| `cubicle run <name> -- <command>` | execute a command under policy guard |
| `cubicle write <name> <path> --data <text>` | guarded write (`--data` omitted → stdin) |
| `cubicle read <name> <path>` | guarded read |
| `cubicle audit <name> [--tail N] [--verify]` | inspect / verify the chain |
| `cubicle report <name> [--format text\|markdown\|json]` | generate a report |
| `cubicle policy <name>` | print the active policy |

Global flags: `--base <dir>` (override the default `~/.agentcubicle` root —
works **before or after** the sub-command) and `--version`.

### The five action types

| action | Meaning | Example target |
| --- | --- | --- |
| `file.read` | read a file | `workspace/a.txt` |
| `file.write` | write a file | `output/report.json` |
| `file.delete` | delete a file | `tmp/cache.bin` |
| `shell.exec` | run a command | `git status` |
| `net.fetch` | network access | `https://api.github.com` |

### Layout

```
~/.agentcubicle/cubicles/<name>/
├── policy.json          # policy document (edit freely)
├── cubicle.json         # metadata
├── workspace/           # agent's main area (writable by default)
├── tmp/                 # scratch space (writable by default)
├── output/              # artefacts (writable by default)
└── audit/audit.jsonl    # hash-chained audit log
```

> ⚠️ **Path base**: every relative path resolves against the **cubicle root**
> (`<name>/` above), *not* `workspace/`. So `workspace/notes.txt` lands on disk
> as `<name>/workspace/notes.txt`.

### Policy configuration

Edit `policy.json` after `cubicle init`. Full structure (defaults shown):

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

| Field | Meaning |
| --- | --- |
| `default_effect` | fallback when no rule matches. `ask` (conservative, default) or `deny` for strict allow-list mode |
| `paths.*` | glob rules. Writing `docs` is equivalent to `docs/**` and covers everything beneath it |
| `commands.allow/deny` | command globs; `deny` is evaluated first and always wins |
| `network.allow_hosts/deny_hosts` | host globs; case, port and path are ignored automatically |
| `budgets.*` | the three budgets; `0` means unlimited |

> 🔐 **Merge semantics**: your policy is deep-merged onto the built-in defaults,
> and **list fields are replaced, not appended**. That is the fail-safe choice
> for a security tool — narrowing an allow-list always takes effect.

Validate a standalone policy file:

```bash
cubicle policy --policy-file ./my-policy.json
```

### Recipes

**Strict allow-list for an agent in CI**

```json
{
  "default_effect": "deny",
  "paths": { "write_allow": ["output/**"] },
  "commands": { "allow": ["python -m pytest*"] },
  "network": { "deny_hosts": ["*"] },
  "budgets": { "max_actions": 30 }
}
```

**Allow a specific API**

```json
{ "network": { "allow_hosts": ["api.github.com", "*.openai.com"], "deny_hosts": [] } }
```

**Feed the verdict back to the LLM**

```python
result = guard.write_file("workspace/x.txt", b"data")
if not result.decision.allowed:
    prompt_hint = f"Action denied: {result.decision.reason} (rule={result.decision.rule})"
```

**Archive an audit report in CI**

```bash
cubicle report demo --format markdown --output audit-report.md
cubicle audit demo --verify || exit 1      # fail the pipeline if the chain broke
```

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | success / allowed |
| `1` | runtime error (missing cubicle, broken chain, …) |
| `3` | **action denied by policy** |
| child's code | `cubicle run` propagates the executed command's exit code |

---

## 💡 Design notes & roadmap

### Philosophy

1. **Denials are auditable too.** Blocked actions are written to the chain —
   *who tried to break out, and when* is often more valuable than *what
   succeeded*.
2. **Explainability over mere enforcement.** A verdict carries
   `reason + rule + risk`, so the agent can understand the boundary and correct
   itself instead of bouncing off a wall.
3. **Conservative by default.** Free reads, scoped writes, no network, and
   `default_effect: ask`. Loosen it explicitly if you must.
4. **Defence in depth.** Path normalisation, escape detection, high-risk
   patterns and environment sanitisation stack up four layers deep.
5. **Zero dependencies is a security property.** Fewer dependencies means a
   smaller supply-chain surface and a cheaper audit.

### Why a hash chain instead of a log file

Edit one line of an ordinary JSONL log and nobody notices. A hash chain makes
every record carry its predecessor's fingerprint:

```
entry[n].prev_hash = entry[n-1].hash
entry[n].hash     = sha256(canonical_json(entry[n]) + prev_hash)
```

Three kinds of tampering, three detections:

| Tampering | Detection |
| --- | --- |
| edit content, **hash not recomputed** | `hash mismatch` |
| edit content, **hash recomputed** | next entry's `prev_hash` no longer matches → `broken link` |
| **delete a whole entry** | sequence numbers gap → `non-contiguous` |

### Tech choices

| Choice | Why |
| --- | --- |
| Standard library only | no supply-chain risk, works offline, installs in a second |
| JSONL storage | appends are atomic, `tail -f` friendly, parseable from any language |
| JSON policy | human readable and machine validatable without a YAML parser |
| `fnmatch` globs | ships with Python, shell-familiar semantics, zero learning curve |
| SHA-256 | universally available, no compliance debate |

### Roadmap

- [ ] 🔁 Audit **replay** — re-run a session from its audit log
- [ ] 🤝 Interactive approval backend for `ask` (TTY / webhook)
- [ ] 📤 Export the chain as Sigstore / in-toto attestations
- [ ] 🧩 Policy template gallery (`--template ci-strict`)
- [ ] 🐳 Optional container-grade isolation backend (today: filesystem level)
- [ ] 📈 Prometheus exporter for audit metrics

Good first contributions: new action types, more high-risk command patterns,
additional documentation languages.

---

## 📦 Packaging & deployment

This is a **CLI tool / Python library**: no per-platform binaries are needed.
Both the sdist and the wheel are **pure Python and cross-platform**
(`py3-none-any`).

### One-shot build

```bash
# macOS / Linux
./scripts/build.sh          # produces dist/*.tar.gz and dist/*.whl
./scripts/build.sh test     # tests only
./scripts/build.sh clean    # remove build artefacts

# Windows
scripts\build.bat
scripts\build.bat test
scripts\build.bat clean
```

### Standard PEP 517 build

```bash
python -m pip install build
python -m build --sdist --wheel
```

### Install from source / editable

```bash
pip install .            # regular install, gives you the `cubicle` command
pip install -e .         # editable, your edits take effect immediately
```

### Deploy on a server

```bash
pip install agentcubicle-1.0.0-py3-none-any.whl
cubicle --base /var/lib/agentcubicle init prod-agent
cubicle --base /var/lib/agentcubicle policy prod-agent > /etc/agentcubicle-policy.json
```

Point `--base` at a persistent directory and add
`cubicle audit <name> --verify` to your regular health checks.

### Tests

```bash
python tests/run_tests.py        # zero-dependency; pytest not required
python -m unittest discover -s tests
```

### Compatibility

| Environment | Status |
| --- | --- |
| Python 3.8 / 3.9 / 3.10 / 3.11 / 3.12 | ✅ supported |
| Windows 10+ / macOS 12+ / Linux | ✅ supported |
| Air-gapped | ✅ fully offline |
| Read-only `$HOME` | ⚠️ pass a writable `--base` |

---

## 🤝 Contributing

PRs and issues are welcome!

**Commit style** (Angular convention)

- `feat: add xxx`
- `fix: correct xxx`
- `docs: update xxx`
- `refactor: restructure xxx`
- `test: cover xxx`
- `chore: build tooling`

**PR checklist**

1. Fork the repo and branch off (`feat/xxx`).
2. Keep the **zero third-party dependency** promise (test-only deps aside).
3. Add unit tests for new logic and keep `python tests/run_tests.py` green.
4. Update the README in every language you touch.
5. Describe the motivation and your test results in the PR.

**Issues**: include your Python version, OS, the exact commands and the full
output. For security reports, redact sensitive paths before posting.

---

## 📄 License

Released under the **[MIT License](LICENSE)**.

- ✅ Commercial use, modification, distribution, private deployment
- ✅ Usable inside closed-source products
- ⚠️ Keep the copyright and license notice
- ❌ No warranty, no liability

> Security note: AgentCubicle provides **filesystem-level** isolation and
> auditing. It is not an OS-level sandbox or a container. When running
> untrusted code, wrap it in a container or VM on top of this tool.

---

<div align="center">

If this helped you, a ⭐ would be much appreciated!

Made with 🛡️ by [gitstq](https://github.com/gitstq)

</div>
