# Contributing to NarrativePPT

运行步骤见 [README](README.md)，代码来源和权利范围见 [NOTICE](docs/NOTICE.md)。

- 一个改动聚焦一个问题，附复现步骤和验证结果。
- 使用虚构或已获授权的材料，不提交私人文档、账号、API Key、`.env` 和运行日志。
- 修改生成或导出时记录模型、材料、页数及失败结果；真实 API 验收需单独手动启动，会消耗额度。
- 保留第三方版权信息，不向整个仓库追加未经授权的许可证。

本地检查：

```bash
cd backend
uv run pytest -q
uv run ruff check app tests
cd ../frontend
npm run build
npm run lint
```

使用开发数据库，测试会创建随机账号与记录。安全问题请按 [SECURITY.md](SECURITY.md) 私下报告。
