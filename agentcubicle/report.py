"""审计报告渲染。

Audit report rendering.

把审计链渲染成人类可读的文本、Markdown 或 JSON，供人工复核或 CI 归档。

Render the audit chain as human readable text, Markdown or JSON for manual
review or CI archival.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from .audit import AuditEntry, summarize
from .paths import readable_size

EFFECT_ICON = {
    "allow": "✅",
    "deny": "⛔",
    "ask": "❓",
}


def _iso(ts: Optional[float]) -> str:
    """把时间戳格式化为 UTC 字符串。

    Format a timestamp as a UTC string.
    """
    if not ts:
        return "-"
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ts))


def render_text(
    cubicle_name: str,
    entries: List[AuditEntry],
    chain_ok: bool,
    problems: Optional[List[str]] = None,
) -> str:
    """渲染纯文本审计报告。

    Render a plain-text audit report.
    """
    stats = summarize(entries)
    lines: List[str] = []
    lines.append("=" * 72)
    lines.append(f"  AgentCubicle Audit Report — cubicle: {cubicle_name}")
    lines.append("=" * 72)
    lines.append(f"  Records        : {stats['total']}")
    lines.append(f"  Window         : {_iso(stats['first_timestamp'])} → {_iso(stats['last_timestamp'])}")
    lines.append(f"  Bytes written  : {readable_size(stats['write_bytes'])}")
    lines.append(f"  Wall time      : {stats['duration_ms'] / 1000.0:.2f}s")
    lines.append(f"  Chain integrity: {'INTACT ✅' if chain_ok else 'BROKEN ⛔'}")
    lines.append("")

    lines.append("-- Decisions by effect " + "-" * 50)
    if stats["by_effect"]:
        for effect, count in sorted(stats["by_effect"].items()):
            icon = EFFECT_ICON.get(effect, "•")
            lines.append(f"  {icon} {effect:<6} {count}")
    else:
        lines.append("  (no records)")
    lines.append("")

    lines.append("-- Actions by type " + "-" * 52)
    if stats["by_action"]:
        for action, count in sorted(stats["by_action"].items()):
            lines.append(f"  • {action:<14} {count}")
    else:
        lines.append("  (no records)")
    lines.append("")

    lines.append("-- Risk distribution " + "-" * 50)
    if stats["by_risk"]:
        for risk, count in sorted(stats["by_risk"].items()):
            lines.append(f"  • {risk:<8} {count}")
    lines.append("")

    if problems:
        lines.append("-- Integrity problems " + "-" * 50)
        for problem in problems:
            lines.append(f"  ⛔ {problem}")
        lines.append("")

    lines.append("-- Timeline " + "-" * 60)
    for entry in entries:
        icon = EFFECT_ICON.get(entry.effect, "•")
        rule = f" [{entry.rule}]" if entry.rule else ""
        lines.append(
            f"  #{entry.seq:<4} {entry.iso_time}  {icon} {entry.effect:<5} "
            f"{entry.action:<12} {entry.target}{rule}"
        )
        if entry.reason:
            lines.append(f"         ↳ {entry.reason}")
    lines.append("=" * 72)
    return "\n".join(lines)


def render_markdown(
    cubicle_name: str,
    entries: List[AuditEntry],
    chain_ok: bool,
    problems: Optional[List[str]] = None,
) -> str:
    """渲染 Markdown 审计报告。

    Render a Markdown audit report.
    """
    stats = summarize(entries)
    lines: List[str] = []
    lines.append(f"# 🛡️ AgentCubicle Audit Report — `{cubicle_name}`")
    lines.append("")
    lines.append(f"- 🔗 **Chain integrity**: {'`INTACT` ✅' if chain_ok else '`BROKEN` ⛔'}")
    lines.append(f"- 📊 **Records**: {stats['total']}")
    lines.append(f"- 💾 **Bytes written**: {readable_size(stats['write_bytes'])}")
    lines.append(f"- ⏱️ **Wall time**: {stats['duration_ms'] / 1000.0:.2f}s")
    lines.append(f"- 🕐 **Window**: {_iso(stats['first_timestamp'])} → {_iso(stats['last_timestamp'])}")
    lines.append("")

    lines.append("## 📈 Decisions")
    lines.append("")
    lines.append("| Effect | Count |")
    lines.append("| --- | ---: |")
    for effect, count in sorted(stats["by_effect"].items()):
        icon = EFFECT_ICON.get(effect, "•")
        lines.append(f"| {icon} `{effect}` | {count} |")
    lines.append("")

    lines.append("## 🧾 Timeline")
    lines.append("")
    lines.append("| # | Time (UTC) | Effect | Action | Target | Rule |")
    lines.append("| ---: | --- | --- | --- | --- | --- |")
    for entry in entries:
        icon = EFFECT_ICON.get(entry.effect, "•")
        target = entry.target.replace("|", "\\|")
        rule = f"`{entry.rule}`" if entry.rule else "-"
        lines.append(
            f"| {entry.seq} | {entry.iso_time} | {icon} `{entry.effect}` | "
            f"`{entry.action}` | `{target}` | {rule} |"
        )
    lines.append("")

    if problems:
        lines.append("## ⛔ Integrity problems")
        lines.append("")
        for problem in problems:
            lines.append(f"- {problem}")
        lines.append("")
    return "\n".join(lines)


def render_json(
    cubicle_name: str,
    entries: List[AuditEntry],
    chain_ok: bool,
    problems: Optional[List[str]] = None,
) -> str:
    """渲染 JSON 审计报告。

    Render a JSON audit report.
    """
    stats = summarize(entries)
    payload: Dict[str, Any] = {
        "cubicle": cubicle_name,
        "chain_ok": chain_ok,
        "problems": problems or [],
        "summary": stats,
        "entries": [entry.to_dict() for entry in entries],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)
