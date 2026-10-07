# Security

不要在公开 issue、PR、截图或附件中提交真实 API Key、密码、连接串、用户材料或完整供应商响应。

发现安全漏洞时，请优先使用仓库 Security 页面的 **Report a vulnerability** 私下报告；若入口不可用，可通过维护者 GitHub 资料中的公开联系方式联系。请提供最小复现和影响范围，不附真实凭证。

- 开发配置只用于本地。公网部署需强随机 JWT / 模型加密密钥、数据库凭证、TLS 和访问控制。
- PostgreSQL 和 Redis 不应直接暴露到公网。
- `MODEL_CONFIG_SECRET` 必须稳定保管，并与数据库备份配套管理。
- 新增 `MODEL_API_ALLOWED_HOSTS` 服务需检查地址和重定向行为。
- `.env`、运行数据、私有模型配置和备份不应进入 Git。

当前没有承诺安全审计认证或固定响应 SLA。
