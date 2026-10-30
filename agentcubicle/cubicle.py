"""隔离工作区（cubicle）管理。

Isolated workspace ("cubicle") management.

一个 cubicle 是 Agent 的专属工位，目录结构如下：

.. code-block:: text

    ~/.agentcubicle/cubicles/<name>/
    ├── policy.json      策略文档
    ├── workspace/       Agent 可自由读写的沙箱目录
    ├── tmp/             临时目录
    ├── output/          产出目录
    └── audit/audit.jsonl 防篡改审计链

A cubicle is a dedicated desk for an agent, laid out as shown above.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .audit import AuditLog
from .paths import ensure_directory
from .policy import Policy
from .version import CONFIG_DIR_NAME

# 每个 cubicle 内的固定子目录
# Fixed sub-directories inside every cubicle
SUBDIRS = ("workspace", "tmp", "output", "audit")


class CubicleError(RuntimeError):
    """工作区操作失败时抛出。

    Raised when a workspace operation fails.
    """


@dataclass
class CubicleInfo:
    """工作区的摘要信息。

    Summary information about a cubicle.
    """

    name: str
    path: str
    policy_name: str
    audit_entries: int
    chain_ok: bool
    created_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典。

        Serialise to a dictionary.
        """
        return {
            "name": self.name,
            "path": self.path,
            "policy_name": self.policy_name,
            "audit_entries": self.audit_entries,
            "chain_ok": self.chain_ok,
            "created_at": self.created_at,
        }


def config_root(base: Optional[str] = None) -> str:
    """返回全局配置根目录（默认 ``~/.agentcubicle``）。

    Return the global configuration root (defaults to ``~/.agentcubicle``).
    """
    if base:
        return os.path.abspath(os.path.expanduser(base))
    return os.path.join(os.path.expanduser("~"), CONFIG_DIR_NAME)


def cubicles_root(base: Optional[str] = None) -> str:
    """返回工作区集合的根目录。

    Return the root directory holding all cubicles.
    """
    return os.path.join(config_root(base), "cubicles")


def validate_name(name: str) -> str:
    """校验并规范化工作区名称，非法名称抛出 :class:`CubicleError`。

    Validate and normalise a cubicle name, raising :class:`CubicleError` for
    invalid input.
    """
    cleaned = (name or "").strip()
    if not cleaned:
        raise CubicleError("cubicle name must not be empty")
    if cleaned in (".", ".."):
        raise CubicleError(f"invalid cubicle name: {name!r}")
    if any(sep in cleaned for sep in ("/", "\\", os.sep)):
        raise CubicleError(f"cubicle name must not contain path separators: {name!r}")
    if any(ch in cleaned for ch in ("\0", "\n", "\r", "\t")):
        raise CubicleError(f"cubicle name contains control characters: {name!r}")
    if not all(ch.isalnum() or ch in "-_." for ch in cleaned):
        raise CubicleError(
            f"cubicle name may only contain letters, digits, '-', '_' and '.': {name!r}"
        )
    return cleaned


class Cubicle:
    """一个隔离工作区。

    A single isolated workspace.
    """

    def __init__(self, name: str, base: Optional[str] = None) -> None:
        self.name = validate_name(name)
        self.base = config_root(base)
        self.path = os.path.join(cubicles_root(self.base), self.name)
        self._policy: Optional[Policy] = None

    # -- 目录访问器 ---------------------------------------------------------
    # Directory accessors

    @property
    def cubicle_root(self) -> str:
        """工作区根目录——所有相对路径的解析基准。

        Cubicle root directory: the base against which every relative path is
        resolved. 策略中的 ``workspace/**`` 等规则都相对这一层。

        Policy rules such as ``workspace/**`` are all relative to this level.
        """
        return self.path

    @property
    def workspace_dir(self) -> str:
        """沙箱可写目录。

        Writable sandbox directory.
        """
        return os.path.join(self.path, "workspace")

    @property
    def tmp_dir(self) -> str:
        """临时目录。

        Temporary directory.
        """
        return os.path.join(self.path, "tmp")

    @property
    def output_dir(self) -> str:
        """产出目录。

        Output directory.
        """
        return os.path.join(self.path, "output")

    @property
    def audit_dir(self) -> str:
        """审计目录。

        Audit directory.
        """
        return os.path.join(self.path, "audit")

    @property
    def policy_file(self) -> str:
        """策略文件路径。

        Policy file path.
        """
        return os.path.join(self.path, "policy.json")

    @property
    def audit_file(self) -> str:
        """审计日志文件路径。

        Audit log file path.
        """
        return os.path.join(self.audit_dir, "audit.jsonl")

    @property
    def exists(self) -> bool:
        """工作区是否已存在。

        Whether the cubicle already exists.
        """
        return os.path.isdir(self.path)

    # -- 生命周期 -----------------------------------------------------------
    # Lifecycle

    def create(
        self,
        policy: Optional[Policy] = None,
        policy_file: Optional[str] = None,
        force: bool = False,
    ) -> "Cubicle":
        """创建工作区目录与初始文件。

        Create the cubicle directories and initial files.
        """
        if self.exists and not force:
            raise CubicleError(
                f"cubicle '{self.name}' already exists (use --force to reinitialise)"
            )
        if self.exists and force:
            shutil.rmtree(self.path)

        ensure_directory(self.path)
        for sub in SUBDIRS:
            ensure_directory(os.path.join(self.path, sub))

        if policy_file:
            loaded = Policy.from_file(policy_file)
        else:
            loaded = policy or Policy.default()
        loaded.save(self.policy_file)

        meta = {
            "name": self.name,
            "created_at": time.time(),
            "version": 1,
        }
        with open(os.path.join(self.path, "cubicle.json"), "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

        self._policy = loaded
        return self

    def remove(self) -> None:
        """删除工作区（含全部数据）。

        Delete the cubicle and all of its data.
        """
        if not self.exists:
            raise CubicleError(f"cubicle '{self.name}' does not exist")
        shutil.rmtree(self.path)
        self._policy = None

    def require(self) -> "Cubicle":
        """确保工作区存在，否则抛异常。

        Ensure the cubicle exists or raise.
        """
        if not self.exists:
            raise CubicleError(
                f"cubicle '{self.name}' does not exist; run `cubicle init {self.name}` first"
            )
        return self

    # -- 策略与审计 ---------------------------------------------------------
    # Policy & audit

    @property
    def policy(self) -> Policy:
        """加载（并缓存）当前工作区的策略。

        Load (and cache) the cubicle policy.
        """
        if self._policy is None:
            self.require()
            if os.path.exists(self.policy_file):
                self._policy = Policy.from_file(self.policy_file)
            else:
                self._policy = Policy.default()
        return self._policy

    def reload_policy(self) -> Policy:
        """强制从磁盘重新加载策略。

        Force-reload the policy from disk.
        """
        self._policy = None
        return self.policy

    @property
    def audit(self) -> AuditLog:
        """返回审计日志句柄。

        Return the audit log handle.
        """
        return AuditLog(self.audit_file)

    def info(self) -> CubicleInfo:
        """返回工作区摘要信息。

        Return summary information about the cubicle.
        """
        self.require()
        audit = self.audit
        ok, _ = audit.verify()
        created_at: Optional[float] = None
        meta_file = os.path.join(self.path, "cubicle.json")
        if os.path.exists(meta_file):
            try:
                with open(meta_file, "r", encoding="utf-8") as fh:
                    created_at = json.load(fh).get("created_at")
            except (ValueError, OSError):
                created_at = None
        return CubicleInfo(
            name=self.name,
            path=self.path,
            policy_name=self.policy.name,
            audit_entries=len(audit),
            chain_ok=ok,
            created_at=created_at,
        )


def list_cubicles(base: Optional[str] = None) -> List[CubicleInfo]:
    """列出全部工作区。

    List every cubicle.
    """
    root = cubicles_root(base)
    results: List[CubicleInfo] = []
    if not os.path.isdir(root):
        return results
    for entry in sorted(os.listdir(root)):
        cubicle_dir = os.path.join(root, entry)
        if not os.path.isdir(cubicle_dir):
            continue
        try:
            results.append(Cubicle(entry, base=base).info())
        except (CubicleError, ValueError, OSError):
            # 跳过非工作区目录，保证 list 永远可用
            # Skip non-cubicle directories so `list` never breaks
            continue
    return results
