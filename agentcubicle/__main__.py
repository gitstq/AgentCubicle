"""允许通过 ``python -m agentcubicle`` 启动 CLI。

Allow launching the CLI via ``python -m agentcubicle``.
"""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
