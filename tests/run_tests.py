#!/usr/bin/env python3
"""零依赖测试运行器（无需 pytest 即可运行全部用例）。

Zero-dependency test runner (runs the whole suite without pytest).

用法 / Usage::

    python tests/run_tests.py            # 运行全部测试
    python tests/run_tests.py -v         # 详细输出
    python -m unittest discover -s tests # 等价方式

退出码 0 表示全部通过，1 表示存在失败。

Exit code 0 means everything passed, 1 means at least one failure.
"""

from __future__ import annotations

import os
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

TEST_PATTERN = "test_*.py"


def build_suite() -> unittest.TestSuite:
    """发现并组装测试套件。

    Discover and assemble the test suite.
    """
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=HERE, pattern=TEST_PATTERN,
                            top_level_dir=HERE)
    return suite


def main(argv: list[str] | None = None) -> int:
    """运行测试并返回退出码。

    Run the tests and return an exit code.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    verbosity = 2 if "-v" in argv or "--verbose" in argv else 1

    print("=" * 70)
    print("  AgentCubicle test suite (zero-dependency)")
    print("=" * 70)

    suite = build_suite()
    started = time.time()
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    elapsed = time.time() - started

    print("-" * 70)
    print(f"  ran {result.testsRun} tests in {elapsed:.2f}s")
    print(f"  failures: {len(result.failures)}  errors: {len(result.errors)}  "
          f"skipped: {len(result.skipped)}")
    if result.wasSuccessful():
        print("  ✅ ALL TESTS PASSED")
        print("=" * 70)
        return 0
    print("  ⛔ TESTS FAILED")
    print("=" * 70)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
