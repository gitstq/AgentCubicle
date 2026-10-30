"""防篡改审计日志（哈希链）。

Tamper-evident audit log (hash chain).

每条审计记录都包含前一条记录的哈希，形成一条只能追加、无法静默篡改的链：

.. code-block:: text

    entry[n].prev_hash = entry[n-1].hash
    entry[n].hash     = sha256(canonical(entry[n] without hash) + prev_hash)

任何对历史记录的修改都会导致后续所有哈希校验失败，:func:`AuditLog.verify`
会精确指出第一条被破坏的记录。

Every audit entry carries the hash of its predecessor, forming an
append-only chain that cannot be silently modified. Any edit to historical
records breaks every subsequent hash, and :func:`AuditLog.verify` pinpoints the
first corrupted entry.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from .version import AUDIT_HASH_ALGO, AUDIT_VERSION

GENESIS_HASH = "0" * 64


def canonical_json(payload: Dict[str, Any]) -> str:
    """把字典序列化为稳定、可复现的 JSON 字符串。

    Serialise a dictionary into a stable, reproducible JSON string.

    键按字典序排序、不使用多余空白、非 ASCII 原样保留，保证同样的内容在任何
    平台上都得到同一个字节序列。

    Keys are sorted, no extra whitespace is emitted and non-ASCII text is kept
    verbatim, so identical content always yields identical bytes on any platform.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def compute_hash(payload: Dict[str, Any], prev_hash: str) -> str:
    """计算单条记录的链上哈希。

    Compute the chain hash of a single entry.
    """
    digest = hashlib.new(AUDIT_HASH_ALGO)
    digest.update(canonical_json(payload).encode("utf-8"))
    digest.update((prev_hash or GENESIS_HASH).encode("utf-8"))
    return digest.hexdigest()


@dataclass
class AuditEntry:
    """一条审计记录。

    A single audit entry.
    """

    seq: int
    timestamp: float
    cubicle: str
    action: str
    target: str
    effect: str
    reason: str = ""
    rule: Optional[str] = None
    risk: str = "low"
    size_bytes: int = 0
    duration_ms: float = 0.0
    exit_code: Optional[int] = None
    prev_hash: str = GENESIS_HASH
    hash: str = ""
    actor: str = "agent"
    extra: Dict[str, Any] = field(default_factory=dict)

    def payload(self) -> Dict[str, Any]:
        """返回参与哈希计算的内容（不含 ``hash`` 字段自身）。

        Return the hashed payload (excluding the ``hash`` field itself).
        """
        return {
            "seq": self.seq,
            "timestamp": round(self.timestamp, 6),
            "cubicle": self.cubicle,
            "action": self.action,
            "target": self.target,
            "effect": self.effect,
            "reason": self.reason,
            "rule": self.rule,
            "risk": self.risk,
            "size_bytes": self.size_bytes,
            "duration_ms": round(self.duration_ms, 3),
            "exit_code": self.exit_code,
            "prev_hash": self.prev_hash,
            "actor": self.actor,
            "extra": self.extra or {},
        }

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典（含哈希）。

        Serialise to a dictionary (hash included).
        """
        data = self.payload()
        data["hash"] = self.hash
        data["audit_version"] = AUDIT_VERSION
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEntry":
        """从字典还原审计记录。

        Rebuild an audit entry from a dictionary.
        """
        return cls(
            seq=int(data.get("seq", 0)),
            timestamp=float(data.get("timestamp", 0.0)),
            cubicle=str(data.get("cubicle", "")),
            action=str(data.get("action", "")),
            target=str(data.get("target", "")),
            effect=str(data.get("effect", "")),
            reason=str(data.get("reason", "")),
            rule=data.get("rule"),
            risk=str(data.get("risk", "low")),
            size_bytes=int(data.get("size_bytes", 0) or 0),
            duration_ms=float(data.get("duration_ms", 0.0) or 0.0),
            exit_code=data.get("exit_code"),
            prev_hash=str(data.get("prev_hash", GENESIS_HASH)),
            hash=str(data.get("hash", "")),
            actor=str(data.get("actor", "agent")),
            extra=dict(data.get("extra") or {}),
        )

    @property
    def iso_time(self) -> str:
        """返回可读的时间戳（UTC）。

        Human readable UTC timestamp.
        """
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.timestamp))


class AuditLog:
    """基于 JSONL 的追加式审计日志。

    Append-only JSONL backed audit log.
    """

    def __init__(self, path: os.PathLike | str) -> None:
        self.path = os.fspath(path)
        self._tail_hash = GENESIS_HASH
        self._seq = 0
        self._loaded = False

    # -- 内部 ---------------------------------------------------------------
    # Internals

    def _ensure_loaded(self) -> None:
        """惰性扫描已有日志，恢复链尾哈希与序号。

        Lazily scan existing records to restore the chain tail hash and sequence.
        """
        if self._loaded:
            return
        self._loaded = True
        if not os.path.exists(self.path):
            return
        with open(self.path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = AuditEntry.from_dict(json.loads(line))
                except (ValueError, TypeError):
                    # 跳过损坏行，但不影响链尾恢复
                    # Skip corrupted lines without breaking tail recovery
                    continue
                self._tail_hash = entry.hash or self._tail_hash
                self._seq = max(self._seq, entry.seq)

    @property
    def last_hash(self) -> str:
        """当前链尾哈希。

        Current tail hash of the chain.
        """
        self._ensure_loaded()
        return self._tail_hash

    @property
    def last_seq(self) -> int:
        """当前最大序号。

        Current largest sequence number.
        """
        self._ensure_loaded()
        return self._seq

    # -- 写入 ---------------------------------------------------------------
    # Writing

    def append(self, **fields: Any) -> AuditEntry:
        """追加一条审计记录并返回它。

        Append an audit entry and return it.

        关键参数：``cubicle``、``action``、``target``、``effect``。其余字段可选。

        Key arguments: ``cubicle``, ``action``, ``target``, ``effect``.
        Everything else is optional.
        """
        self._ensure_loaded()
        self._seq += 1
        entry = AuditEntry(
            seq=self._seq,
            timestamp=fields.pop("timestamp", time.time()),
            cubicle=fields.pop("cubicle", ""),
            action=fields.pop("action", ""),
            target=fields.pop("target", ""),
            effect=fields.pop("effect", ""),
            prev_hash=self._tail_hash,
            **fields,
        )
        entry.hash = compute_hash(entry.payload(), entry.prev_hash)
        self._tail_hash = entry.hash

        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        return entry

    # -- 读取 ---------------------------------------------------------------
    # Reading

    def read_all(self) -> List[AuditEntry]:
        """读取全部记录（按文件顺序）。

        Read every entry in file order.
        """
        entries: List[AuditEntry] = []
        if not os.path.exists(self.path):
            return entries
        with open(self.path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(AuditEntry.from_dict(json.loads(line)))
                except (ValueError, TypeError):
                    continue
        return entries

    def tail(self, count: int = 20) -> List[AuditEntry]:
        """返回最后 ``count`` 条记录。

        Return the last ``count`` entries.
        """
        entries = self.read_all()
        return entries[-count:] if count > 0 else entries

    def __iter__(self) -> Iterator[AuditEntry]:  # pragma: no cover - convenience
        """按顺序迭代记录。

        Iterate entries in order.
        """
        return iter(self.read_all())

    def __len__(self) -> int:
        """记录总数。

        Total number of entries.
        """
        return len(self.read_all())

    # -- 校验 ---------------------------------------------------------------
    # Verification

    def verify(self) -> Tuple[bool, List[str]]:
        """完整校验哈希链，返回 ``(是否完好, 问题列表)``。

        Verify the whole hash chain, returning ``(ok, problems)``.
        """
        problems: List[str] = []
        expected_prev = GENESIS_HASH
        seen_seq: Optional[int] = None

        for entry in self.read_all():
            recomputed = compute_hash(entry.payload(), entry.prev_hash)
            if recomputed != entry.hash:
                problems.append(
                    f"entry #{entry.seq}: hash mismatch "
                    f"(stored={entry.hash[:12]}..., recomputed={recomputed[:12]}...)"
                )
            if entry.prev_hash != expected_prev:
                problems.append(
                    f"entry #{entry.seq}: broken link "
                    f"(prev_hash={entry.prev_hash[:12]}..., "
                    f"expected={expected_prev[:12]}...)"
                )
            if seen_seq is not None and entry.seq != seen_seq + 1:
                problems.append(
                    f"entry #{entry.seq}: non-contiguous sequence (previous was {seen_seq})"
                )
            expected_prev = entry.hash
            seen_seq = entry.seq

        return (not problems), problems


def summarize(entries: Iterable[AuditEntry]) -> Dict[str, Any]:
    """把审计记录汇总为统计信息。

    Summarise audit entries into statistics.
    """
    total = 0
    by_effect: Dict[str, int] = {}
    by_action: Dict[str, int] = {}
    by_risk: Dict[str, int] = {}
    write_bytes = 0
    duration_ms = 0.0
    first_ts: Optional[float] = None
    last_ts: Optional[float] = None

    for entry in entries:
        total += 1
        by_effect[entry.effect] = by_effect.get(entry.effect, 0) + 1
        by_action[entry.action] = by_action.get(entry.action, 0) + 1
        by_risk[entry.risk] = by_risk.get(entry.risk, 0) + 1
        write_bytes += max(0, int(entry.size_bytes or 0))
        duration_ms += max(0.0, float(entry.duration_ms or 0.0))
        if first_ts is None or entry.timestamp < first_ts:
            first_ts = entry.timestamp
        if last_ts is None or entry.timestamp > last_ts:
            last_ts = entry.timestamp

    return {
        "total": total,
        "by_effect": dict(sorted(by_effect.items())),
        "by_action": dict(sorted(by_action.items())),
        "by_risk": dict(sorted(by_risk.items())),
        "write_bytes": write_bytes,
        "duration_ms": round(duration_ms, 3),
        "first_timestamp": first_ts,
        "last_timestamp": last_ts,
    }


def new_session_id() -> str:
    """生成一个新的会话 ID（用于把一批动作分组）。

    Generate a fresh session id used to group a batch of actions.
    """
    return uuid.uuid4().hex[:12]
