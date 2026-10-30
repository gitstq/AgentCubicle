"""受策略约束的动作执行器。

Policy-aware action executor.

执行器是「决策」与「动作」之间唯一的桥梁：任何真实副作用都必须经过
:meth:`Guard.run`，先裁决、再执行、最后落审计。被拒绝的动作不会产生任何副作用，
但仍会留下一条 ``deny`` 审计记录——**拒绝本身也是需要被审计的事件**。

The executor is the only bridge between decisions and actions: every real side
effect must go through :meth:`Guard.run`, which decides first, executes second
and records last. Denied actions cause no side effect but still produce a
``deny`` audit entry — **a denial is itself an auditable event**.
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .audit import AuditEntry, AuditLog
from .cubicle import Cubicle
from .paths import normalize_relative, readable_size
from .policy import Decision, Policy
from .version import (
    ACTION_FILE_DELETE,
    ACTION_FILE_READ,
    ACTION_FILE_WRITE,
    ACTION_SHELL_EXEC,
    EFFECT_ALLOW,
    EFFECT_DENY,
)


class GuardDenied(RuntimeError):
    """动作被策略拒绝时抛出。

    Raised when an action is denied by policy.
    """


@dataclass
class ExecutionResult:
    """一次受控执行的完整结果。

    The complete result of a guarded execution.
    """

    decision: Decision
    entry: AuditEntry
    executed: bool = False
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    data: Optional[bytes] = None

    @property
    def allowed(self) -> bool:
        """是否被允许执行。

        Whether the action was allowed.
        """
        return self.decision.allowed

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典。

        Serialise to a dictionary.
        """
        return {
            "executed": self.executed,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "decision": self.decision.to_dict(),
            "audit_seq": self.entry.seq,
        }


class Guard:
    """策略守卫：把决策、执行、审计串成闭环。

    Policy guard: closes the loop between decision, execution and audit.
    """

    def __init__(
        self,
        cubicle: Cubicle,
        policy: Optional[Policy] = None,
        actor: str = "agent",
        session: str = "",
    ) -> None:
        self.cubicle = cubicle
        self.policy = policy or cubicle.policy
        self.actor = actor
        self.session = session
        self.audit: AuditLog = cubicle.audit

    # -- 内部 ---------------------------------------------------------------
    # Internals

    def _record(
        self,
        action: str,
        target: str,
        decision: Decision,
        size_bytes: int = 0,
        duration_ms: float = 0.0,
        exit_code: Optional[int] = None,
        executed: bool = False,
    ) -> AuditEntry:
        """写入一条审计记录。

        Write one audit entry.
        """
        return self.audit.append(
            cubicle=self.cubicle.name,
            action=action,
            target=target,
            effect=decision.effect,
            reason=decision.reason,
            rule=decision.rule,
            risk=decision.risk,
            size_bytes=size_bytes,
            duration_ms=duration_ms,
            exit_code=exit_code,
            actor=self.actor,
            extra={"session": self.session, "executed": executed},
        )

    def _decide(self, action: str, target: str, size_bytes: int = 0) -> Decision:
        """在工作区根目录上下文中裁决动作。

        Decide an action within the cubicle root context.
        """
        return self.policy.evaluate(
            action, target, root=self.cubicle.cubicle_root, size_bytes=size_bytes
        )

    # -- 文件动作 -----------------------------------------------------------
    # File actions

    def read_file(self, rel_path: str) -> ExecutionResult:
        """受控读取文件。

        Guarded file read.
        """
        decision = self._decide(ACTION_FILE_READ, rel_path)
        started = time.time()
        if not decision.allowed:
            entry = self._record(ACTION_FILE_READ, rel_path, decision)
            return ExecutionResult(decision, entry, executed=False)

        try:
            _, absolute = normalize_relative(rel_path, self.cubicle.cubicle_root)
            with open(absolute, "rb") as handle:
                payload = handle.read()
        except (OSError, ValueError) as exc:
            denied = Decision(EFFECT_DENY, f"read failed: {exc}", rule=None, risk="low")
            entry = self._record(ACTION_FILE_READ, rel_path, denied)
            return ExecutionResult(denied, entry, executed=False)

        elapsed = (time.time() - started) * 1000.0
        self.policy.record(ACTION_FILE_READ, size_bytes=len(payload))
        entry = self._record(
            ACTION_FILE_READ, rel_path, decision,
            size_bytes=len(payload), duration_ms=elapsed, executed=True,
        )
        return ExecutionResult(decision, entry, executed=True, data=payload)

    def write_file(self, rel_path: str, data: bytes) -> ExecutionResult:
        """受控写入文件。

        Guarded file write.
        """
        payload = data if isinstance(data, bytes) else str(data).encode("utf-8")
        decision = self._decide(ACTION_FILE_WRITE, rel_path, size_bytes=len(payload))
        started = time.time()
        if not decision.allowed:
            entry = self._record(ACTION_FILE_WRITE, rel_path, decision)
            return ExecutionResult(decision, entry, executed=False)

        try:
            _, absolute = normalize_relative(rel_path, self.cubicle.cubicle_root)
            os.makedirs(os.path.dirname(absolute), exist_ok=True)
            with open(absolute, "wb") as handle:
                handle.write(payload)
        except (OSError, ValueError) as exc:
            denied = Decision(EFFECT_DENY, f"write failed: {exc}", rule=None, risk="low")
            entry = self._record(ACTION_FILE_WRITE, rel_path, denied)
            return ExecutionResult(denied, entry, executed=False)

        elapsed = (time.time() - started) * 1000.0
        self.policy.record(ACTION_FILE_WRITE, size_bytes=len(payload))
        entry = self._record(
            ACTION_FILE_WRITE, rel_path, decision,
            size_bytes=len(payload), duration_ms=elapsed, executed=True,
        )
        return ExecutionResult(decision, entry, executed=True)

    def delete_file(self, rel_path: str) -> ExecutionResult:
        """受控删除文件。

        Guarded file deletion.
        """
        decision = self._decide(ACTION_FILE_DELETE, rel_path)
        started = time.time()
        if not decision.allowed:
            entry = self._record(ACTION_FILE_DELETE, rel_path, decision)
            return ExecutionResult(decision, entry, executed=False)

        try:
            _, absolute = normalize_relative(rel_path, self.cubicle.cubicle_root)
            os.remove(absolute)
        except (OSError, ValueError) as exc:
            denied = Decision(EFFECT_DENY, f"delete failed: {exc}", rule=None, risk="low")
            entry = self._record(ACTION_FILE_DELETE, rel_path, denied)
            return ExecutionResult(denied, entry, executed=False)

        elapsed = (time.time() - started) * 1000.0
        self.policy.record(ACTION_FILE_DELETE)
        entry = self._record(
            ACTION_FILE_DELETE, rel_path, decision,
            duration_ms=elapsed, executed=True,
        )
        return ExecutionResult(decision, entry, executed=True)

    # -- 命令执行 -----------------------------------------------------------
    # Command execution

    def run_command(
        self,
        command: str,
        timeout: Optional[float] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        """受控执行 shell 命令。

        Guarded shell execution.

        命令在工作区目录内以清洗后的环境变量运行，超时受预算限制，
        并通过 ``subprocess`` 直接执行（不经过 ``shell=True`` 之外的额外解释器）。

        The command runs inside the workspace directory with a sanitised
        environment, is bounded by the timeout budget, and is launched through
        ``subprocess`` without any additional interpreter indirection.
        """
        decision = self._decide(ACTION_SHELL_EXEC, command)
        started = time.time()
        if not decision.allowed:
            entry = self._record(ACTION_SHELL_EXEC, command, decision)
            return ExecutionResult(decision, entry, executed=False)

        budgets = self.policy.budgets
        limit = timeout
        if limit is None:
            max_runtime = float(budgets.get("max_runtime_seconds", 0) or 0)
            limit = max_runtime if max_runtime > 0 else 60.0

        runtime_env = _sanitized_env(self.cubicle, env)
        cwd = self.cubicle.workspace_dir
        os.makedirs(cwd, exist_ok=True)

        try:
            completed = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                env=runtime_env,
                capture_output=True,
                timeout=limit,
            )
            stdout = _decode(completed.stdout)
            stderr = _decode(completed.stderr)
            exit_code = int(completed.returncode)
        except subprocess.TimeoutExpired:
            elapsed = (time.time() - started) * 1000.0
            denied = Decision(
                EFFECT_DENY,
                f"command timed out after {limit:.1f}s",
                rule="budgets.max_runtime_seconds",
                risk="medium",
            )
            entry = self._record(
                ACTION_SHELL_EXEC, command, denied,
                duration_ms=elapsed, executed=True, exit_code=124,
            )
            return ExecutionResult(
                denied, entry, executed=True, stdout="",
                stderr=f"timeout after {limit:.1f}s", exit_code=124,
            )
        except OSError as exc:
            elapsed = (time.time() - started) * 1000.0
            denied = Decision(
                EFFECT_DENY, f"command failed to start: {exc}", rule=None, risk="medium"
            )
            entry = self._record(
                ACTION_SHELL_EXEC, command, denied,
                duration_ms=elapsed, executed=False,
            )
            return ExecutionResult(denied, entry, executed=False, stderr=str(exc))

        elapsed = (time.time() - started) * 1000.0
        self.policy.record(ACTION_SHELL_EXEC, seconds=elapsed / 1000.0)
        entry = self._record(
            ACTION_SHELL_EXEC, command, decision,
            duration_ms=elapsed, exit_code=exit_code, executed=True,
        )
        return ExecutionResult(
            decision, entry, executed=True,
            stdout=stdout, stderr=stderr, exit_code=exit_code,
        )

    # -- 批量预检 -----------------------------------------------------------
    # Batch dry-run

    def dry_run(self, actions: List[Tuple[str, str]]) -> List[Decision]:
        """对一组动作只裁决不执行（用于事前审批）。

        Decide a batch of actions without executing them (pre-approval).
        """
        results: List[Decision] = []
        for action, target in actions:
            results.append(self._decide(action, target))
        return results


def _decode(raw: Any) -> str:
    """把子进程输出安全解码为字符串。

    Decode subprocess output into a string safely.
    """
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return str(raw)


def _sanitized_env(
    cubicle: Cubicle,
    extra: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """构造清洗后的子进程环境。

    Build a sanitised environment for the child process.

    只保留 PATH / HOME / LANG / TMPDIR 等必要变量，并注入 cubicle 相关路径，
    避免把宿主的全部凭据与配置泄漏给 Agent。

    Only PATH / HOME / LANG / TMPDIR style variables survive, plus cubicle
    specific paths, so host credentials and configuration never leak into the
    agent process.
    """
    keep = (
        "PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "TEMP", "TMP",
        "SYSTEMROOT", "COMSPEC", "PYTHONIOENCODING",
    )
    runtime_env: Dict[str, str] = {}
    for key in keep:
        value = os.environ.get(key)
        if value:
            runtime_env[key] = value
    runtime_env["CUBICLE_NAME"] = cubicle.name
    runtime_env["CUBICLE_ROOT"] = cubicle.path
    runtime_env["CUBICLE_WORKSPACE"] = cubicle.workspace_dir
    runtime_env["CUBICLE_OUTPUT"] = cubicle.output_dir
    runtime_env["CUBICLE_TMP"] = cubicle.tmp_dir
    if extra:
        runtime_env.update({str(k): str(v) for k, v in extra.items()})
    return runtime_env


def format_decision(decision: Decision) -> str:
    """把裁决格式化为单行文本。

    Format a decision as a single line of text.
    """
    rule = f"  rule={decision.rule}" if decision.rule else ""
    return f"{decision.effect.upper():<5} risk={decision.risk:<6} {decision.reason}{rule}"


def format_size(num_bytes: int) -> str:
    """格式化字节数（复用 :func:`~agentcubicle.paths.readable_size`）。

    Format a byte count (delegates to :func:`~agentcubicle.paths.readable_size`).
    """
    return readable_size(num_bytes)
