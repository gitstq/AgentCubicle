"""AgentCubicle —— 面向 AI Agent 的隔离工作区、动作授权与防篡改审计。

AgentCubicle — isolated workspaces, pre-action authorization and tamper-evident
audit for AI agents.

只依赖 Python 标准库，零第三方依赖、完全离线可用。

Depends only on the Python standard library: zero third-party dependencies and
fully offline.

典型用法 / Typical usage::

    from agentcubicle import Cubicle, Guard

    cubicle = Cubicle("demo")
    if not cubicle.exists:
        cubicle.create()

    guard = Guard(cubicle)
    result = guard.write_file("workspace/notes.txt", b"hello")
    print(result.decision.effect)   # allow / deny / ask
"""

from .audit import AuditEntry, AuditLog, compute_hash, summarize
from .cubicle import Cubicle, CubicleError, CubicleInfo, list_cubicles
from .executor import ExecutionResult, Guard, GuardDenied
from .paths import PathEscapeError, normalize_command, normalize_relative
from .policy import Decision, Policy, PolicyError, Usage
from .version import PROJECT_NAME, PROJECT_SLUG, __version__

__all__ = [
    "__version__",
    "PROJECT_NAME",
    "PROJECT_SLUG",
    "AuditEntry",
    "AuditLog",
    "compute_hash",
    "summarize",
    "Cubicle",
    "CubicleError",
    "CubicleInfo",
    "list_cubicles",
    "ExecutionResult",
    "Guard",
    "GuardDenied",
    "PathEscapeError",
    "normalize_command",
    "normalize_relative",
    "Decision",
    "Policy",
    "PolicyError",
    "Usage",
]
