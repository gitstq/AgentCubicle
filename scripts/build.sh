#!/usr/bin/env bash
#
# AgentCubicle 一键构建脚本（POSIX / macOS / Linux）
# AgentCubicle one-shot build script (POSIX / macOS / Linux)
#
# 用法 / Usage:
#   ./scripts/build.sh          # 构建 sdist + wheel
#   ./scripts/build.sh clean    # 清理构建产物
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON:-}"
if [ -z "$PYTHON_BIN" ]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    PYTHON_BIN="python"
  fi
fi

log() { printf '\033[36m[build]\033[0m %s\n' "$*"; }
err() { printf '\033[31m[build]\033[0m %s\n' "$*" >&2; }

case "${1:-build}" in
  clean)
    log "cleaning build artifacts..."
    rm -rf build dist ./*.egg-info
    find . -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
    log "done ✅"
    ;;
  test)
    log "running the standard-library test suite..."
    "$PYTHON_BIN" tests/run_tests.py
    ;;
  build|*)
    log "using interpreter: $PYTHON_BIN ($("$PYTHON_BIN" --version 2>&1))"

    if [ -d dist ]; then
      log "removing previous dist/"
      rm -rf dist
    fi

    log "running tests before packaging..."
    "$PYTHON_BIN" tests/run_tests.py

    if "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
      if "$PYTHON_BIN" -c "import build" >/dev/null 2>&1; then
        log "building sdist + wheel with PEP 517 build..."
        "$PYTHON_BIN" -m build --sdist --wheel
      elif "$PYTHON_BIN" -c "import setuptools, wheel" >/dev/null 2>&1; then
        log "building sdist + wheel with setuptools..."
        "$PYTHON_BIN" setup.py sdist bdist_wheel
      else
        log "building sdist with setuptools (wheel module unavailable)..."
        "$PYTHON_BIN" setup.py sdist
      fi
    else
      log "pip unavailable; building sdist via setuptools..."
      "$PYTHON_BIN" setup.py sdist
    fi

    log "artifacts:"
    ls -1 dist 2>/dev/null | sed 's/^/  - /' || err "no artifacts produced"
    log "build finished ✅"
    ;;
esac
