"""版本与元数据常量。

Version and metadata constants.
"""

__version__ = "1.0.0"

PROJECT_NAME = "AgentCubicle"
PROJECT_SLUG = "agentcubicle"

# 默认配置根目录名称（位于用户主目录下）
# Default configuration root directory name (under the user home directory)
CONFIG_DIR_NAME = ".agentcubicle"

# 策略文件格式版本
# Policy file format version
POLICY_VERSION = 1

# 审计日志文件格式版本
# Audit log file format version
AUDIT_VERSION = 1

# 审计链使用的哈希算法
# Hash algorithm used by the audit chain
AUDIT_HASH_ALGO = "sha256"

# 受支持的决策取值
# Supported decision effects
EFFECT_ALLOW = "allow"
EFFECT_DENY = "deny"
EFFECT_ASK = "ask"
EFFECTS = (EFFECT_ALLOW, EFFECT_DENY, EFFECT_ASK)

# 受支持的动作类型
# Supported action types
ACTION_FILE_READ = "file.read"
ACTION_FILE_WRITE = "file.write"
ACTION_FILE_DELETE = "file.delete"
ACTION_SHELL_EXEC = "shell.exec"
ACTION_NET_FETCH = "net.fetch"
ACTIONS = (
    ACTION_FILE_READ,
    ACTION_FILE_WRITE,
    ACTION_FILE_DELETE,
    ACTION_SHELL_EXEC,
    ACTION_NET_FETCH,
)
