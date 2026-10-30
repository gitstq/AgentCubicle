"""工作区路径安全工具。

Workspace path-safety utilities.

所有对外暴露的函数都只依赖 Python 标准库，并且保证：

* 任何路径都会被归一化并解析为绝对路径；
* 任何包含 ``..`` 逃逸、符号链接逃逸的路径都会被拒绝；
* 匹配规则在归一化后的**相对 posix 路径**上进行，避免 Windows 与 POSIX
  分隔符差异导致的绕过。

All public helpers rely only on the Python standard library and guarantee that:

* every path is normalised and resolved to an absolute path;
* any path escaping the workspace root via ``..`` or symlinks is rejected;
* glob rules are evaluated against normalised **relative posix paths**, so
  separator differences between Windows and POSIX cannot be used to bypass rules.
"""

from __future__ import annotations

import fnmatch
import os
import posixpath
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


class PathEscapeError(ValueError):
    """路径试图逃逸出工作区根目录时抛出。

    Raised when a path attempts to escape the workspace root directory.
    """


def normalize_relative(path: str, root: os.PathLike | str) -> Tuple[str, Path]:
    """把 ``path`` 归一化到 ``root`` 之内，返回 ``(相对 posix 路径, 绝对路径)``。

    当 ``path`` 为绝对或相对路径但解析后落在 ``root`` 之外时抛出
    :class:`PathEscapeError`。

    Normalise ``path`` inside ``root`` and return ``(relative posix path,
    absolute path)``. Raises :class:`PathEscapeError` when the resolved path
    falls outside ``root``.
    """
    root_abs = Path(os.path.abspath(os.fspath(root)))
    raw = os.fspath(path)

    # 前导分隔符一律剥离：绝对路径在工作区语义下同样被视为「相对工作区根」，
    # 从而避免 "/etc/passwd" 这类输入绕过沙箱。
    # Leading separators are always stripped: within workspace semantics an
    # absolute path is still treated as "relative to the workspace root", so
    # inputs like "/etc/passwd" cannot escape the sandbox.
    raw_relative = raw.lstrip("/\\")
    candidate = Path(os.path.abspath(os.path.join(str(root_abs), raw_relative)))

    try:
        resolved = candidate.resolve()
    except OSError:
        # 路径不存在时 resolve() 仍会返回规范化结果；OSError 只在极端情况下出现，
        # 此时退化为不解析符号链接的绝对路径即可。
        # resolve() normally succeeds for non-existing paths; fall back to the
        # unresolved absolute path when the filesystem misbehaves.
        resolved = candidate

    root_resolved = Path(os.path.abspath(str(root_abs)))
    try:
        root_resolved = root_abs.resolve()
    except OSError:
        root_resolved = root_abs

    try:
        relative = resolved.relative_to(root_resolved)
    except ValueError as exc:  # pragma: no cover - defensive branch
        raise PathEscapeError(
            f"path escapes the workspace root: {raw!r}"
        ) from exc

    rel_posix = relative.as_posix()
    # 归一化掉 "./" 与空片段，保证匹配规则行为一致
    # Normalise away "./" and empty segments so rule matching stays consistent
    rel_posix = posixpath.normpath(rel_posix) if rel_posix else "."
    if rel_posix == ".":
        rel_posix = ""
    return rel_posix, Path(os.path.join(str(root_abs), rel_posix))


def is_within(path: str, root: os.PathLike | str) -> bool:
    """判断 ``path`` 是否位于 ``root`` 之内（不抛异常版本）。

    Non-raising variant of :func:`normalize_relative`.
    """
    try:
        normalize_relative(path, root)
        return True
    except PathEscapeError:
        return False


def match_any(rel_path: str, patterns: Optional[Iterable[str]]) -> Optional[str]:
    """用 glob 规则列表匹配相对路径，返回首个命中规则；无命中返回 ``None``。

    Match ``rel_path`` against a list of glob patterns and return the first hit,
    or ``None`` when nothing matches.

    规则同时匹配自身与「目录下所有内容」两种语义：``workspace`` 等价于
    ``workspace/**``，方便使用者书写。

    A rule also matches everything beneath it: ``workspace`` is equivalent to
    ``workspace/**``, which keeps policies readable.
    """
    if not patterns:
        return None
    target = (rel_path or "").strip("/")
    for pattern in patterns:
        pat = (pattern or "").strip()
        if not pat:
            continue
        pat = pat.lstrip("./") if pat.startswith("./") else pat
        pat = pat.rstrip("/")
        if not pat or pat == "*" or pat == "**":
            return pattern
        candidates = [pat, pat + "/**"] if not pat.endswith("*") else [pat]
        for cand in candidates:
            if fnmatch.fnmatch(target, cand):
                return pattern
        # 目录前缀匹配：规则 docs 应命中 docs/a/b.txt
        # Directory prefix match: rule `docs` should hit `docs/a/b.txt`
        if target == pat or target.startswith(pat + "/"):
            return pattern
    return None


def normalize_command(command: str) -> str:
    """归一化 shell 命令用于规则匹配：折叠空白、统一小写比较基准。

    Normalise a shell command for rule matching by collapsing whitespace.
    The original case is preserved (rules are case-sensitive on purpose) but
    surrounding noise is removed.
    """
    return " ".join((command or "").split())


def command_matches(command: str, patterns: Optional[Iterable[str]]) -> Optional[str]:
    """用 glob 规则列表匹配命令字符串，返回首个命中规则。

    Match ``command`` against shell-style glob patterns, returning the first hit.
    """
    if not patterns:
        return None
    cmd = normalize_command(command)
    if not cmd:
        return None
    for pattern in patterns:
        pat = normalize_command(pattern)
        if not pat:
            continue
        if fnmatch.fnmatch(cmd, pat):
            return pattern
    return None


def split_host_port(url_or_host: str) -> str:
    """从 URL 或 ``host[:port]`` 中提取规范化主机名（小写、去端口）。

    Extract a normalised hostname (lowercased, port stripped) from a URL or a
    ``host[:port]`` string.
    """
    value = (url_or_host or "").strip()
    if not value:
        return ""
    lowered = value.lower()
    if "://" in lowered:
        lowered = lowered.split("://", 1)[1]
    lowered = lowered.split("/", 1)[0]
    lowered = lowered.split("?", 1)[0]
    if "@" in lowered:
        lowered = lowered.rsplit("@", 1)[1]
    if lowered.startswith("["):  # IPv6 literal
        return lowered
    if ":" in lowered:
        lowered = lowered.split(":", 1)[0]
    return lowered


def host_matches(url_or_host: str, patterns: Optional[Iterable[str]]) -> Optional[str]:
    """用 glob 规则列表匹配主机名，返回首个命中规则。

    Match a hostname against glob patterns, returning the first hit.
    """
    if not patterns:
        return None
    host = split_host_port(url_or_host)
    if not host:
        return None
    for pattern in patterns:
        pat = (pattern or "").strip().lower()
        if not pat:
            continue
        if pat in ("*", "**"):
            return pattern
        if fnmatch.fnmatch(host, pat):
            return pattern
    return None


def ensure_directory(path: os.PathLike | str) -> Path:
    """确保目录存在并返回其 :class:`~pathlib.Path`。

    Ensure ``path`` exists as a directory and return it as a
    :class:`~pathlib.Path`.
    """
    target = Path(os.path.abspath(os.fspath(path)))
    target.mkdir(parents=True, exist_ok=True)
    return target


def readable_size(num_bytes: int) -> str:
    """把字节数格式化为人类可读字符串。

    Format a byte count as a human readable string.
    """
    size = float(max(0, int(num_bytes)))
    units: List[str] = ["B", "KB", "MB", "GB", "TB"]
    idx = 0
    while size >= 1024 and idx < len(units) - 1:
        size /= 1024.0
        idx += 1
    if idx == 0:
        return f"{int(size)} {units[idx]}"
    return f"{size:.2f} {units[idx]}"
