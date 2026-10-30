"""AgentCubicle 命令行接口。

AgentCubicle command line interface.

命令总览 / Command overview::

    cubicle init <name>              创建隔离工作区
    cubicle list                     列出所有工作区
    cubicle info <name>              查看工作区详情
    cubicle rm <name>                删除工作区
    cubicle check <action> <target>  事前裁决（不执行）
    cubicle run <name> -- <command>  受控执行命令
    cubicle write <name> <path>      受控写入文件（stdin 或 --data）
    cubicle read  <name> <path>      受控读取文件
    cubicle audit <name>             查看/校验审计链
    cubicle report <name>            生成审计报告
    cubicle policy <name>            查看策略
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence

from .audit import new_session_id
from .cubicle import Cubicle, CubicleError, list_cubicles
from .executor import Guard, format_decision
from .paths import readable_size
from .policy import DEFAULT_POLICY, Policy, PolicyError
from .report import render_json, render_markdown, render_text
from .version import (
    ACTIONS,
    ACTION_FILE_READ,
    ACTION_FILE_WRITE,
    EFFECT_DENY,
    PROJECT_NAME,
    PROJECT_SLUG,
    __version__,
)

EXIT_OK = 0
EXIT_DENIED = 3
EXIT_ERROR = 1

ICON = {
    "allow": "✅",
    "deny": "⛔",
    "ask": "❓",
}


# ---------------------------------------------------------------------------
# 辅助函数
# Helpers
# ---------------------------------------------------------------------------


def _print(text: str = "") -> None:
    """向标准输出打印一行。

    Print a line to stdout.
    """
    sys.stdout.write(text + "\n")


def _fail(message: str, code: int = EXIT_ERROR) -> int:
    """向标准错误输出错误信息并返回退出码。

    Print an error to stderr and return an exit code.
    """
    sys.stderr.write(f"⛔ {message}\n")
    return code


def _load_cubicle(name: str, base: Optional[str] = None) -> Cubicle:
    """加载并校验工作区。

    Load and validate a cubicle.
    """
    cubicle = Cubicle(name, base=base)
    cubicle.require()
    return cubicle


def _guard(args: argparse.Namespace, cubicle: Cubicle) -> Guard:
    """构造守卫对象。

    Build a guard instance.
    """
    return Guard(
        cubicle,
        actor=getattr(args, "actor", "agent") or "agent",
        session=getattr(args, "session", "") or new_session_id(),
    )


# ---------------------------------------------------------------------------
# 子命令实现
# Sub-command implementations
# ---------------------------------------------------------------------------


def cmd_init(args: argparse.Namespace) -> int:
    """``cubicle init`` —— 创建工作区。

    Create a cubicle.
    """
    try:
        cubicle = Cubicle(args.name, base=args.base)
        policy = None
        if args.policy:
            policy = Policy.from_file(args.policy)
        cubicle.create(policy=policy, force=args.force)
    except (CubicleError, PolicyError, OSError) as exc:
        return _fail(str(exc))

    _print(f"🎉 cubicle '{cubicle.name}' ready at {cubicle.path}")
    _print(f"   📁 workspace : {cubicle.workspace_dir}")
    _print(f"   📁 output    : {cubicle.output_dir}")
    _print(f"   🔐 policy    : {cubicle.policy_file}")
    _print(f"   🧾 audit     : {cubicle.audit_file}")
    _print("   ➡️  next: cubicle check file.write workspace/demo.txt")
    return EXIT_OK


def cmd_list(args: argparse.Namespace) -> int:
    """``cubicle list`` —— 列出工作区。

    List cubicles.
    """
    infos = list_cubicles(args.base)
    if not infos:
        _print("(no cubicles yet) run: cubicle init <name>")
        return EXIT_OK

    if args.json:
        _print(json.dumps([i.to_dict() for i in infos], indent=2, ensure_ascii=False))
        return EXIT_OK

    _print(f"📦 {len(infos)} cubicle(s):")
    _print("")
    _print(f"  {'NAME':<20} {'POLICY':<12} {'AUDIT':>7}  {'CHAIN':<8} CREATED")
    _print("  " + "-" * 66)
    for info in infos:
        created = "-"
        if info.created_at:
            created = _fmt_time(info.created_at)
        chain = "✅ intact" if info.chain_ok else "⛔ broken"
        _print(
            f"  {info.name:<20} {info.policy_name:<12} {info.audit_entries:>7}  "
            f"{chain:<8} {created}"
        )
    return EXIT_OK


def _fmt_time(ts: float) -> str:
    """格式化时间戳为日期。

    Format a timestamp as a date.
    """
    import time as _time

    return _time.strftime("%Y-%m-%d", _time.gmtime(ts))


def cmd_info(args: argparse.Namespace) -> int:
    """``cubicle info`` —— 查看工作区详情。

    Show cubicle details.
    """
    try:
        cubicle = _load_cubicle(args.name, args.base)
        info = cubicle.info()
    except CubicleError as exc:
        return _fail(str(exc))

    if args.json:
        _print(json.dumps(info.to_dict(), indent=2, ensure_ascii=False))
        return EXIT_OK

    policy = cubicle.policy
    budgets = policy.budgets
    _print(f"📦 cubicle: {info.name}")
    _print(f"   path      : {info.path}")
    _print(f"   policy    : {policy.name} (default: {policy.default_effect})")
    _print(f"   audit     : {info.audit_entries} entries, chain "
           f"{'✅ intact' if info.chain_ok else '⛔ broken'}")
    _print(f"   budgets   : actions={budgets.get('max_actions')}, "
           f"write={readable_size(int(budgets.get('max_write_bytes') or 0))}, "
           f"runtime={budgets.get('max_runtime_seconds')}s")
    return EXIT_OK


def cmd_rm(args: argparse.Namespace) -> int:
    """``cubicle rm`` —— 删除工作区。

    Remove a cubicle.
    """
    try:
        cubicle = _load_cubicle(args.name, args.base)
    except CubicleError as exc:
        return _fail(str(exc))

    if not args.yes:
        _print(f"⚠️  about to delete cubicle '{cubicle.name}' at {cubicle.path}")
        _print("   re-run with --yes to confirm")
        return EXIT_OK
    try:
        cubicle.remove()
    except (CubicleError, OSError) as exc:
        return _fail(str(exc))
    _print(f"🗑️  cubicle '{args.name}' removed")
    return EXIT_OK


def cmd_check(args: argparse.Namespace) -> int:
    """``cubicle check`` —— 事前裁决，不产生副作用。

    Pre-action verdict without side effects.
    """
    try:
        cubicle = _load_cubicle(args.name, args.base)
    except CubicleError as exc:
        return _fail(str(exc))

    policy = cubicle.policy
    decisions = []
    for target in args.targets:
        decisions.append(
            policy.evaluate(args.action, target, root=cubicle.cubicle_root)
        )

    worst_deny = any(d.effect == EFFECT_DENY for d in decisions)

    if args.json:
        payload: Dict[str, Any] = {
            "cubicle": cubicle.name,
            "action": args.action,
            "results": [
                {"target": t, **d.to_dict()} for t, d in zip(args.targets, decisions)
            ],
        }
        _print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for target, decision in zip(args.targets, decisions):
            icon = ICON.get(decision.effect, "•")
            _print(f"{icon} {decision.effect.upper():<5} {args.action:<12} {target}")
            _print(f"      reason : {decision.reason}")
            if decision.rule:
                _print(f"      rule   : {decision.rule}")
            _print(f"      risk   : {decision.risk}")
    return EXIT_DENIED if worst_deny else EXIT_OK


def cmd_run(args: argparse.Namespace) -> int:
    """``cubicle run`` —— 受控执行命令。

    Guarded command execution.
    """
    try:
        cubicle = _load_cubicle(args.name, args.base)
    except CubicleError as exc:
        return _fail(str(exc))

    command = " ".join(args.command).strip()
    if not command:
        return _fail("no command supplied; usage: cubicle run <name> -- <command>")

    guard = _guard(args, cubicle)
    result = guard.run_command(command, timeout=args.timeout)

    if args.json:
        _print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        _print(format_decision(result.decision))
        if result.executed:
            if result.stdout:
                _print("--- stdout ---")
                _print(result.stdout.rstrip())
            if result.stderr:
                _print("--- stderr ---")
                _print(result.stderr.rstrip())
            _print(f"--- exit={result.exit_code} "
                   f"audit_seq={result.entry.seq} ---")

    if not result.decision.allowed:
        return EXIT_DENIED
    return result.exit_code or EXIT_OK


def cmd_write(args: argparse.Namespace) -> int:
    """``cubicle write`` —— 受控写入文件。

    Guarded file write.
    """
    try:
        cubicle = _load_cubicle(args.name, args.base)
    except CubicleError as exc:
        return _fail(str(exc))

    if args.data is not None:
        payload = args.data.encode("utf-8")
    else:
        payload = sys.stdin.buffer.read()

    guard = _guard(args, cubicle)
    result = guard.write_file(args.path, payload)

    if args.json:
        _print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        _print(format_decision(result.decision))
        if result.executed:
            _print(f"💾 wrote {readable_size(len(payload))} to {args.path} "
                   f"(audit_seq={result.entry.seq})")
    return EXIT_OK if result.decision.allowed else EXIT_DENIED


def cmd_read(args: argparse.Namespace) -> int:
    """``cubicle read`` —— 受控读取文件。

    Guarded file read.
    """
    try:
        cubicle = _load_cubicle(args.name, args.base)
    except CubicleError as exc:
        return _fail(str(exc))

    guard = _guard(args, cubicle)
    result = guard.read_file(args.path)

    if not result.decision.allowed:
        if args.json:
            _print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        else:
            _print(format_decision(result.decision))
        return EXIT_DENIED

    if args.json:
        payload = {
            **result.to_dict(),
            "content": (result.data or b"").decode("utf-8", errors="replace"),
        }
        _print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        sys.stdout.write((result.data or b"").decode("utf-8", errors="replace"))
    return EXIT_OK


def cmd_audit(args: argparse.Namespace) -> int:
    """``cubicle audit`` —— 查看与校验审计链。

    Inspect and verify the audit chain.
    """
    try:
        cubicle = _load_cubicle(args.name, args.base)
    except CubicleError as exc:
        return _fail(str(exc))

    audit = cubicle.audit
    ok, problems = audit.verify()

    if args.verify:
        if ok:
            _print("✅ audit chain intact — no tampering detected")
            return EXIT_OK
        _print("⛔ audit chain broken:")
        for problem in problems:
            _print(f"   - {problem}")
        return EXIT_ERROR

    entries = audit.tail(args.tail)
    if args.json:
        _print(json.dumps(
            {
                "cubicle": cubicle.name,
                "chain_ok": ok,
                "problems": problems,
                "entries": [e.to_dict() for e in entries],
            },
            indent=2, ensure_ascii=False,
        ))
        return EXIT_OK

    if not entries:
        _print("(audit log is empty)")
        return EXIT_OK

    _print(f"🧾 last {len(entries)} audit entries "
           f"(chain {'✅ intact' if ok else '⛔ broken'}):")
    _print("")
    for entry in entries:
        icon = ICON.get(entry.effect, "•")
        rule = f" [{entry.rule}]" if entry.rule else ""
        _print(f"  #{entry.seq:<4} {entry.iso_time}  {icon} {entry.effect:<5} "
               f"{entry.action:<12} {entry.target}{rule}")
    if problems:
        _print("")
        _print("⛔ integrity problems:")
        for problem in problems:
            _print(f"   - {problem}")
    return EXIT_OK


def cmd_report(args: argparse.Namespace) -> int:
    """``cubicle report`` —— 生成审计报告。

    Generate an audit report.
    """
    try:
        cubicle = _load_cubicle(args.name, args.base)
    except CubicleError as exc:
        return _fail(str(exc))

    audit = cubicle.audit
    ok, problems = audit.verify()
    entries = audit.read_all()
    if args.only_denied:
        entries = [e for e in entries if e.effect == EFFECT_DENY]

    if args.format == "json":
        output = render_json(cubicle.name, entries, ok, problems)
    elif args.format == "markdown":
        output = render_markdown(cubicle.name, entries, ok, problems)
    else:
        output = render_text(cubicle.name, entries, ok, problems)

    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(output + "\n")
        _print(f"📄 report written to {args.output}")
    else:
        _print(output)
    return EXIT_OK


def cmd_policy(args: argparse.Namespace) -> int:
    """``cubicle policy`` —— 查看或校验策略。

    Show or validate a policy.
    """
    if args.policy_file:
        try:
            policy = Policy.from_file(args.policy_file)
        except (PolicyError, OSError, ValueError) as exc:
            return _fail(str(exc))
        _print(f"✅ policy file '{args.policy_file}' is valid")
        _print(json.dumps(policy.to_dict(), indent=2, ensure_ascii=False))
        return EXIT_OK

    try:
        cubicle = _load_cubicle(args.name, args.base)
    except CubicleError as exc:
        return _fail(str(exc))

    if args.show_defaults:
        _print(json.dumps(DEFAULT_POLICY, indent=2, ensure_ascii=False))
        return EXIT_OK

    _print(json.dumps(cubicle.policy.to_dict(), indent=2, ensure_ascii=False))
    return EXIT_OK


# ---------------------------------------------------------------------------
# 参数解析
# Argument parsing
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """构造命令行解析器。

    Build the CLI argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="cubicle",
        description=(
            "🛡️ AgentCubicle — zero-dependency isolated workspaces, "
            "pre-action authorization and tamper-evident audit for AI agents."
        ),
        epilog=(
            "examples:\n"
            "  cubicle init demo\n"
            "  cubicle check demo file.write workspace/notes.txt\n"
            "  cubicle run demo -- ls -la\n"
            "  cubicle audit demo --verify\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version",
                        version=f"{PROJECT_NAME} {__version__}")
    parser.add_argument("--base", default=None,
                        help="override the ~/.agentcubicle config root")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # init
    p_init = sub.add_parser("init", help="create an isolated cubicle")
    p_init.add_argument("name", help="cubicle name")
    p_init.add_argument("--policy", default=None, help="custom policy JSON file")
    p_init.add_argument("--force", action="store_true",
                        help="reinitialise an existing cubicle")
    p_init.set_defaults(func=cmd_init)

    # list
    p_list = sub.add_parser("list", help="list all cubicles")
    p_list.add_argument("--json", action="store_true", help="emit JSON")
    p_list.set_defaults(func=cmd_list)

    # info
    p_info = sub.add_parser("info", help="show cubicle details")
    p_info.add_argument("name")
    p_info.add_argument("--json", action="store_true", help="emit JSON")
    p_info.set_defaults(func=cmd_info)

    # rm
    p_rm = sub.add_parser("rm", help="remove a cubicle")
    p_rm.add_argument("name")
    p_rm.add_argument("--yes", action="store_true", help="confirm deletion")
    p_rm.set_defaults(func=cmd_rm)

    # check
    p_check = sub.add_parser(
        "check", help="pre-action verdict (no side effects)"
    )
    p_check.add_argument("name")
    p_check.add_argument("action", choices=list(ACTIONS),
                         help="action type to evaluate")
    p_check.add_argument("targets", nargs="+",
                         help="one or more targets (path / command / url)")
    p_check.add_argument("--json", action="store_true", help="emit JSON")
    p_check.set_defaults(func=cmd_check)

    # run
    p_run = sub.add_parser("run", help="run a command under policy guard")
    p_run.add_argument("name")
    p_run.add_argument("command", nargs=argparse.REMAINDER,
                       help="command to run (prefix with --)")
    p_run.add_argument("--timeout", type=float, default=None,
                       help="override the runtime budget in seconds")
    p_run.add_argument("--actor", default="agent", help="actor label in audit")
    p_run.add_argument("--session", default="", help="session id for grouping")
    p_run.add_argument("--json", action="store_true", help="emit JSON")
    p_run.set_defaults(func=cmd_run)

    # write
    p_write = sub.add_parser("write", help="write a file under policy guard")
    p_write.add_argument("name")
    p_write.add_argument("path", help="path relative to the workspace")
    p_write.add_argument("--data", default=None,
                         help="content to write (defaults to stdin)")
    p_write.add_argument("--actor", default="agent")
    p_write.add_argument("--session", default="")
    p_write.add_argument("--json", action="store_true", help="emit JSON")
    p_write.set_defaults(func=cmd_write)

    # read
    p_read = sub.add_parser("read", help="read a file under policy guard")
    p_read.add_argument("name")
    p_read.add_argument("path")
    p_read.add_argument("--actor", default="agent")
    p_read.add_argument("--session", default="")
    p_read.add_argument("--json", action="store_true", help="emit JSON")
    p_read.set_defaults(func=cmd_read)

    # audit
    p_audit = sub.add_parser("audit", help="inspect and verify the audit chain")
    p_audit.add_argument("name")
    p_audit.add_argument("--tail", type=int, default=20, help="show last N entries")
    p_audit.add_argument("--verify", action="store_true",
                         help="only verify chain integrity")
    p_audit.add_argument("--json", action="store_true", help="emit JSON")
    p_audit.set_defaults(func=cmd_audit)

    # report
    p_report = sub.add_parser("report", help="generate an audit report")
    p_report.add_argument("name")
    p_report.add_argument("--format", choices=("text", "markdown", "json"),
                          default="text")
    p_report.add_argument("--output", default=None, help="write report to file")
    p_report.add_argument("--only-denied", action="store_true",
                          help="include denied actions only")
    p_report.set_defaults(func=cmd_report)

    # policy
    p_policy = sub.add_parser("policy", help="show or validate a policy")
    p_policy.add_argument("name", nargs="?", default=None)
    p_policy.add_argument("--policy-file", default=None,
                          help="validate a standalone policy JSON file")
    p_policy.add_argument("--show-defaults", action="store_true",
                          help="print the built-in default policy")
    p_policy.set_defaults(func=cmd_policy)

    return parser


def _extract_base(argv: Sequence[str]) -> tuple[list[str], Optional[str]]:
    """从任意位置提取 ``--base``，使它在子命令前后都能生效。

    Extract ``--base`` from anywhere so it works before or after a sub-command.

    ``argparse`` 的子解析器会用自己的默认值覆盖父解析器的同名参数，因此这里
    手动预处理 argv，保证 ``cubicle list --base /tmp`` 与
    ``cubicle --base /tmp list`` 行为一致。

    ``argparse`` sub-parsers override parent defaults for same-named options,
    so argv is pre-processed here to make ``cubicle list --base /tmp`` behave
    exactly like ``cubicle --base /tmp list``.
    """
    cleaned: list[str] = []
    base: Optional[str] = None
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--base":
            if index + 1 < len(argv):
                base = argv[index + 1]
                index += 2
                continue
        elif token.startswith("--base="):
            base = token.split("=", 1)[1]
            index += 1
            continue
        cleaned.append(token)
        index += 1
    return cleaned, base


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI 入口，返回进程退出码。

    CLI entry point; returns the process exit code.
    """
    raw = list(sys.argv[1:] if argv is None else argv)
    cleaned, base_override = _extract_base(raw)

    parser = build_parser()
    args = parser.parse_args(cleaned)

    if base_override:
        args.base = base_override

    if not getattr(args, "command", None):
        parser.print_help()
        return EXIT_OK

    try:
        return int(args.func(args))
    except CubicleError as exc:
        return _fail(str(exc))
    except PolicyError as exc:
        return _fail(str(exc))
    except KeyboardInterrupt:  # pragma: no cover
        return _fail("interrupted", code=130)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
