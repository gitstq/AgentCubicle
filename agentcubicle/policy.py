"""策略模型与动作前置决策引擎。

Policy model and pre-action decision engine.

决策引擎是 AgentCubicle 的核心：Agent 在执行任何动作（读写文件、执行命令、
访问网络）之前，必须先向引擎申请裁决，得到 ``allow`` / ``deny`` / ``ask``
三种结果之一，并附带可解释的理由与命中的规则。

The decision engine is the heart of AgentCubicle: before an agent performs any
action (file I/O, shell execution, network access) it must ask the engine for a
verdict, receiving ``allow`` / ``deny`` / ``ask`` plus an explainable reason and
the rule that fired.
"""

from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .paths import (
    command_matches,
    host_matches,
    match_any,
    normalize_command,
    normalize_relative,
)
from .version import (
    ACTION_FILE_DELETE,
    ACTION_FILE_READ,
    ACTION_FILE_WRITE,
    ACTION_NET_FETCH,
    ACTION_SHELL_EXEC,
    EFFECT_ALLOW,
    EFFECT_ASK,
    EFFECT_DENY,
    EFFECTS,
    POLICY_VERSION,
)

# ---------------------------------------------------------------------------
# 默认策略
# Default policy
# ---------------------------------------------------------------------------

DEFAULT_POLICY: Dict[str, Any] = {
    "version": POLICY_VERSION,
    "name": "default",
    "description": (
        "Conservative default: free reads, workspace-scoped writes, "
        "no shell escapes, no network."
    ),
    "default_effect": EFFECT_ASK,
    "paths": {
        "read_allow": ["**"],
        "read_deny": [".git/config", "**/.ssh/**", "**/.aws/**"],
        "write_allow": ["workspace/**", "tmp/**", "output/**"],
        "write_deny": [
            ".env",
            "**/.env",
            "**/.git/**",
            "**/.ssh/**",
            "**/*.pem",
            "**/*.key",
        ],
        "delete_deny": ["**"],
    },
    "commands": {
        "allow": [
            "ls*",
            "cat *",
            "echo *",
            "pwd",
            "git status*",
            "git diff*",
            "git log*",
            "python -m pytest*",
            "python -m unittest*",
            "python3 -m pytest*",
        ],
        "deny": [
            "rm -rf *",
            "rm -fr *",
            "sudo *",
            "su *",
            "chmod 777 *",
            "chown *",
            "curl *",
            "wget *",
            "nc *",
            "mkfs*",
            "dd *",
            "* > /dev/sda*",
            ":(){ *",
        ],
    },
    "network": {
        "allow_hosts": [],
        "deny_hosts": ["*"],
    },
    "budgets": {
        "max_actions": 200,
        "max_write_bytes": 10 * 1024 * 1024,
        "max_runtime_seconds": 600,
    },
}

# 高危 shell 模式：即使不在 deny 列表里也会被拦截（纵深防御）
# High-risk shell patterns blocked even when absent from the deny list
# (defence in depth).
DANGEROUS_PATTERNS: List[Dict[str, str]] = [
    {
        "pattern": "*|*sh*",
        "reason": "piping into a shell interpreter is not permitted",
    },
    {
        "pattern": "*|*bash*",
        "reason": "piping into a shell interpreter is not permitted",
    },
    {
        "pattern": "*`*`*",
        "reason": "command substitution is not permitted",
    },
    {
        "pattern": "*$(*)*",
        "reason": "command substitution is not permitted",
    },
    {
        "pattern": "*>/dev/sd*",
        "reason": "writing to a block device is not permitted",
    },
    {
        "pattern": "rm*-rf*/*",
        "reason": "recursive force deletion outside the workspace is not permitted",
    },
    {
        "pattern": "*:(){*",
        "reason": "fork bombs are not permitted",
    },
]


class PolicyError(ValueError):
    """策略文件非法时抛出。

    Raised when a policy document is invalid.
    """


@dataclass
class Decision:
    """一次动作裁决的结果。

    The result of a single action verdict.

    :param effect: ``allow`` / ``deny`` / ``ask`` 之一。
    :param reason: 人类可读的裁决理由。
    :param rule: 命中的策略规则（若有）。
    :param risk: ``low`` / ``medium`` / ``high`` 风险等级。
    """

    effect: str
    reason: str
    rule: Optional[str] = None
    risk: str = "low"

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典。

        Serialise to a dictionary.
        """
        return {
            "effect": self.effect,
            "reason": self.reason,
            "rule": self.rule,
            "risk": self.risk,
        }

    @property
    def allowed(self) -> bool:
        """是否允许执行（``ask`` 视为未授权）。

        Whether execution is allowed (``ask`` counts as not authorised).
        """
        return self.effect == EFFECT_ALLOW

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        rule_part = f" (rule: {self.rule})" if self.rule else ""
        return f"[{self.effect.upper()}] {self.reason}{rule_part}"


@dataclass
class Usage:
    """预算使用量计数器。

    Budget usage counters.
    """

    actions: int = 0
    write_bytes: int = 0
    runtime_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典。

        Serialise to a dictionary.
        """
        return {
            "actions": self.actions,
            "write_bytes": self.write_bytes,
            "runtime_seconds": round(self.runtime_seconds, 3),
        }


@dataclass
class Policy:
    """一份可执行的策略文档。

    An executable policy document.
    """

    data: Dict[str, Any] = field(default_factory=lambda: copy.deepcopy(DEFAULT_POLICY))
    usage: Usage = field(default_factory=Usage)

    # -- 构造与序列化 -------------------------------------------------------
    # Construction & serialisation

    @classmethod
    def default(cls) -> "Policy":
        """返回内置默认策略的副本。

        Return a copy of the built-in default policy.
        """
        return cls(copy.deepcopy(DEFAULT_POLICY))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Policy":
        """从字典构建并做完整性校验。

        Build from a dictionary and validate the structure.
        """
        validate_policy(data)
        merged = merge_policy(copy.deepcopy(DEFAULT_POLICY), data)
        return cls(merged)

    @classmethod
    def from_file(cls, path: os.PathLike | str) -> "Policy":
        """从 JSON 文件加载策略。

        Load a policy from a JSON file.
        """
        with open(os.fspath(path), "r", encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))

    def to_dict(self) -> Dict[str, Any]:
        """导出为可序列化的字典。

        Export as a serialisable dictionary.
        """
        return copy.deepcopy(self.data)

    def save(self, path: os.PathLike | str) -> None:
        """把策略写入 JSON 文件（UTF-8、缩进 2、保留换行）。

        Write the policy to a JSON file (UTF-8, 2-space indent, trailing newline).
        """
        with open(os.fspath(path), "w", encoding="utf-8") as handle:
            json.dump(self.data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

    # -- 便捷访问器 ---------------------------------------------------------
    # Convenience accessors

    @property
    def name(self) -> str:
        """策略名称。

        Policy name.
        """
        return str(self.data.get("name", "default"))

    @property
    def default_effect(self) -> str:
        """兜底决策取值。

        Fallback decision effect.
        """
        effect = str(self.data.get("default_effect", EFFECT_ASK)).lower()
        return effect if effect in EFFECTS else EFFECT_ASK

    @property
    def budgets(self) -> Dict[str, Any]:
        """预算限制字典。

        Budget limits.
        """
        return dict(self.data.get("budgets", {}))

    # -- 决策入口 -----------------------------------------------------------
    # Decision entry points

    def evaluate(
        self,
        action: str,
        target: str = "",
        root: os.PathLike | str = ".",
        size_bytes: int = 0,
    ) -> Decision:
        """对单个动作进行裁决。

        Return a verdict for a single action.

        :param action: 动作类型，如 ``file.write`` / ``shell.exec``。
        :param target: 动作目标：路径、命令或 URL。
        :param root: 工作区根目录，用于路径逃逸检测。
        :param size_bytes: 写入字节数（用于写预算校验）。
        """
        action = (action or "").strip().lower()
        if action not in (ACTION_FILE_READ, ACTION_FILE_WRITE, ACTION_FILE_DELETE,
                          ACTION_SHELL_EXEC, ACTION_NET_FETCH):
            return Decision(
                EFFECT_DENY,
                f"unknown action type: {action!r}",
                rule=None,
                risk="medium",
            )

        # 预算优先：动作次数超限一律拒绝
        # Budgets first: exceeding the action cap is always a denial.
        budget_decision = self._check_budget(size_bytes)
        if budget_decision is not None:
            return budget_decision

        if action in (ACTION_FILE_READ, ACTION_FILE_WRITE, ACTION_FILE_DELETE):
            return self._evaluate_path(action, target, root)
        if action == ACTION_SHELL_EXEC:
            return self._evaluate_command(target)
        return self._evaluate_network(target)

    # -- 内部实现 -----------------------------------------------------------
    # Internal implementation

    def _check_budget(self, size_bytes: int = 0) -> Optional[Decision]:
        """校验预算限制，超限返回 :class:`Decision`，否则返回 ``None``。

        Validate budgets; return a :class:`Decision` when a limit is exceeded,
        otherwise ``None``.
        """
        budgets = self.budgets
        max_actions = int(budgets.get("max_actions", 0) or 0)
        max_write = int(budgets.get("max_write_bytes", 0) or 0)
        if max_actions > 0 and self.usage.actions >= max_actions:
            return Decision(
                EFFECT_DENY,
                f"action budget exhausted ({self.usage.actions}/{max_actions})",
                rule="budgets.max_actions",
                risk="high",
            )
        if max_write > 0 and size_bytes > 0:
            projected = self.usage.write_bytes + int(size_bytes)
            if projected > max_write:
                return Decision(
                    EFFECT_DENY,
                    f"write budget exceeded ({projected}/{max_write} bytes)",
                    rule="budgets.max_write_bytes",
                    risk="high",
                )
        return None

    def _evaluate_path(
        self,
        action: str,
        target: str,
        root: os.PathLike | str,
    ) -> Decision:
        """裁决文件类动作。

        Decide file actions.
        """
        paths_cfg = self.data.get("paths", {})

        # 1) 逃逸检测（最高优先级）
        # 1) Escape detection (highest priority)
        try:
            rel_path, _ = normalize_relative(target, root)
        except Exception as exc:
            return Decision(
                EFFECT_DENY,
                f"path rejected: {exc}",
                rule="paths.escape",
                risk="high",
            )

        if action == ACTION_FILE_READ:
            deny_rule = match_any(rel_path, paths_cfg.get("read_deny"))
            if deny_rule:
                return Decision(
                    EFFECT_DENY,
                    f"read denied for sensitive path '{target}'",
                    rule=f"paths.read_deny:{deny_rule}",
                    risk="high",
                )
            allow_rule = match_any(rel_path, paths_cfg.get("read_allow"))
            if allow_rule:
                return Decision(
                    EFFECT_ALLOW,
                    f"read allowed for '{target}'",
                    rule=f"paths.read_allow:{allow_rule}",
                    risk="low",
                )
            return self._fallback(f"no read rule matched '{target}'")

        if action == ACTION_FILE_WRITE:
            deny_rule = match_any(rel_path, paths_cfg.get("write_deny"))
            if deny_rule:
                return Decision(
                    EFFECT_DENY,
                    f"write denied for sensitive path '{target}'",
                    rule=f"paths.write_deny:{deny_rule}",
                    risk="high",
                )
            allow_rule = match_any(rel_path, paths_cfg.get("write_allow"))
            if allow_rule:
                return Decision(
                    EFFECT_ALLOW,
                    f"write allowed for '{target}'",
                    rule=f"paths.write_allow:{allow_rule}",
                    risk="low",
                )
            return self._fallback(
                f"write target '{target}' is outside the writable area",
                risk="medium",
            )

        # file.delete
        deny_rule = match_any(rel_path, paths_cfg.get("delete_deny"))
        if deny_rule:
            return Decision(
                EFFECT_DENY,
                f"delete denied for '{target}'",
                rule=f"paths.delete_deny:{deny_rule}",
                risk="high",
            )
        allow_rule = match_any(rel_path, paths_cfg.get("delete_allow"))
        if allow_rule:
            return Decision(
                EFFECT_ALLOW,
                f"delete allowed for '{target}'",
                rule=f"paths.delete_allow:{allow_rule}",
                risk="medium",
            )
        return self._fallback(
            f"no delete rule matched '{target}'",
            risk="medium",
        )

    def _evaluate_command(self, command: str) -> Decision:
        """裁决 shell 执行命令。

        Decide shell execution actions.
        """
        normalized = normalize_command(command)
        if not normalized:
            return Decision(
                EFFECT_DENY, "empty command", rule="commands.empty", risk="low"
            )

        commands_cfg = self.data.get("commands", {})

        # 1) 纵深防御：高危模式
        # 1) Defence in depth: high-risk patterns
        for entry in DANGEROUS_PATTERNS:
            from .paths import command_matches as _cm

            if _cm(normalized, [entry["pattern"]]):
                return Decision(
                    EFFECT_DENY,
                    entry["reason"],
                    rule=f"commands.dangerous:{entry['pattern']}",
                    risk="high",
                )

        # 2) 显式 deny 列表
        # 2) Explicit deny list
        deny_rule = command_matches(normalized, commands_cfg.get("deny"))
        if deny_rule:
            return Decision(
                EFFECT_DENY,
                f"command denied by policy: '{normalized}'",
                rule=f"commands.deny:{deny_rule}",
                risk="high",
            )

        # 3) 显式 allow 列表
        # 3) Explicit allow list
        allow_rule = command_matches(normalized, commands_cfg.get("allow"))
        if allow_rule:
            return Decision(
                EFFECT_ALLOW,
                f"command allowed: '{normalized}'",
                rule=f"commands.allow:{allow_rule}",
                risk="medium",
            )

        return self._fallback(
            f"command '{normalized}' is not on the allow list",
            risk="medium",
        )

    def _evaluate_network(self, url: str) -> Decision:
        """裁决网络访问动作。

        Decide network access actions.
        """
        net_cfg = self.data.get("network", {})
        deny_rule = host_matches(url, net_cfg.get("deny_hosts"))
        if deny_rule:
            return Decision(
                EFFECT_DENY,
                f"network access denied for '{url}'",
                rule=f"network.deny_hosts:{deny_rule}",
                risk="high",
            )
        allow_rule = host_matches(url, net_cfg.get("allow_hosts"))
        if allow_rule:
            return Decision(
                EFFECT_ALLOW,
                f"network access allowed for '{url}'",
                rule=f"network.allow_hosts:{allow_rule}",
                risk="medium",
            )
        return self._fallback(
            f"host '{url}' is not on the network allow list",
            risk="high",
        )

    def _fallback(self, reason: str, risk: str = "medium") -> Decision:
        """按 ``default_effect`` 生成兜底裁决。

        Produce the fallback verdict based on ``default_effect``.
        """
        return Decision(
            self.default_effect,
            f"{reason}; falling back to '{self.default_effect}'",
            rule="default_effect",
            risk=risk,
        )

    # -- 使用量记账 ---------------------------------------------------------
    # Usage accounting

    def record(self, action: str, size_bytes: int = 0, seconds: float = 0.0) -> None:
        """记录一次已执行动作的资源消耗。

        Record resource usage for one executed action.
        """
        self.usage.actions += 1
        self.usage.write_bytes += max(0, int(size_bytes))
        self.usage.runtime_seconds += max(0.0, float(seconds))


# ---------------------------------------------------------------------------
# 校验与合并
# Validation & merging
# ---------------------------------------------------------------------------


def validate_policy(data: Dict[str, Any]) -> None:
    """校验策略文档结构，非法时抛出 :class:`PolicyError`。

    Validate a policy document, raising :class:`PolicyError` when invalid.
    """
    if not isinstance(data, dict):
        raise PolicyError("policy must be a JSON object")

    version = data.get("version", POLICY_VERSION)
    if not isinstance(version, int) or version != POLICY_VERSION:
        raise PolicyError(
            f"unsupported policy version: {version!r} (expected {POLICY_VERSION})"
        )

    default_effect = str(data.get("default_effect", EFFECT_ASK)).lower()
    if default_effect not in EFFECTS:
        raise PolicyError(
            f"invalid default_effect: {default_effect!r} "
            f"(expected one of {', '.join(EFFECTS)})"
        )

    for section in ("paths", "commands", "network", "budgets"):
        value = data.get(section)
        if value is not None and not isinstance(value, dict):
            raise PolicyError(f"policy section '{section}' must be an object")

    for key in ("read_allow", "read_deny", "write_allow", "write_deny",
                "delete_allow", "delete_deny"):
        values = data.get("paths", {}).get(key)
        if values is not None and not isinstance(values, list):
            raise PolicyError(f"paths.{key} must be a list of glob patterns")

    for key in ("allow", "deny"):
        values = data.get("commands", {}).get(key)
        if values is not None and not isinstance(values, list):
            raise PolicyError(f"commands.{key} must be a list of glob patterns")

    for key in ("allow_hosts", "deny_hosts"):
        values = data.get("network", {}).get(key)
        if values is not None and not isinstance(values, list):
            raise PolicyError(f"network.{key} must be a list of host globs")

    budgets = data.get("budgets", {})
    if budgets:
        for key in ("max_actions", "max_write_bytes", "max_runtime_seconds"):
            value = budgets.get(key)
            if value is not None:
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    raise PolicyError(f"budgets.{key} must be a number")
                if value < 0:
                    raise PolicyError(f"budgets.{key} must be non-negative")


def merge_policy(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """把用户策略深度合并到默认策略之上。

    列表类型字段采用「覆盖」而非「拼接」，避免默认白名单在用户收窄时仍然生效
    ——这是安全工具的默认安全（fail-safe）取向。

    Deep-merge a user policy on top of the defaults.

    List fields are **replaced**, not concatenated, so that narrowing a default
    allow-list actually takes effect — the fail-safe orientation expected from a
    security tool.
    """
    result = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key].update(copy.deepcopy(value))
        else:
            result[key] = copy.deepcopy(value)
    return result
