# 🤝 贡献指南 / Contributing

感谢你愿意为 AgentCubicle 出力！

## 开发约定

- **零第三方依赖是项目底线**（测试依赖除外）。新增功能请优先使用 Python 标准库。
- 支持 Python **3.8 及以上**，不要使用更高版本才有的语法或标准库 API。
- 所有公开函数、类、模块都需要中英双语 docstring。
- 路径处理必须走 `agentcubicle/paths.py`，禁止在别处自行拼接路径。

## 本地开发

```bash
git clone https://github.com/gitstq/AgentCubicle.git
cd AgentCubicle
pip install -e .
python tests/run_tests.py
```

## 提交规范（Angular）

| 前缀 | 用途 |
| --- | --- |
| `feat:` | 新增功能 |
| `fix:` | 修复缺陷 |
| `docs:` | 文档更新 |
| `refactor:` | 代码重构 |
| `test:` | 测试用例 |
| `chore:` | 构建 / 工具链 |

示例：`feat: 新增 net.fetch 动作的域名白名单匹配`

## Pull Request 检查清单

- [ ] `python tests/run_tests.py` 全绿（83+ 用例）
- [ ] 新增逻辑有对应单元测试
- [ ] 更新了受影响的 README（简中 / 繁中 / English / 日本語）
- [ ] 未引入第三方运行时依赖
- [ ] 提交信息符合 Angular 规范

## Issue 反馈

请附上：Python 版本、操作系统、完整命令与输出。
安全问题请先隐去敏感路径再描述。

## 行为准则

保持友善、就事论事。技术分歧欢迎讨论，人身攻击一律删除。
