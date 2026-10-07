# 部署与运行

NarrativePPT 已在 Linux 用户目录下完成部署与真实模型验收。当前实例位于受限网络，不提供公共在线试用链接；以下地址均为本地示例，请按自己的环境配置。

## Windows 本地运行

参考 [README 快速运行](../README.md#快速运行)。启动脚本会安装依赖、构建前端、执行数据库迁移并启动 API / worker。

## Linux 用户目录部署

没有 sudo 或 Docker 时，可使用独立 conda 环境运行 PostgreSQL、Redis、API 和 worker。目录约定：

| 路径 | 用途 |
|---|---|
| `app/` | 代码、共享布局与前端构建产物 |
| `runtime/` | Python、PostgreSQL、Redis、uv、Supervisor |
| `data/` | 数据库、队列和上传文件 |
| `logs/`、`run/` | 日志及进程状态 |
| `model-config.json`、`secrets.json` | 私有模型和服务配置，禁止提交 |

先在开发机完成前端构建，再执行 `backend/.venv/Scripts/python.exe scripts/package_server.py`（Windows）或对应 Python 命令。代码包及独立模型配置输出至已忽略的 `backend/var/deploy/`。

将代码包解压到服务器 `$HOME/apps/narrative-ppt/app/`，把私有模型配置放在部署根目录并设为 600 权限。不要将模型配置放进代码包。

```bash
ROOT="$HOME/apps/narrative-ppt"
umask 077
conda create -y -p "$ROOT/runtime" --override-channels -c conda-forge python=3.12 postgresql=16 redis-server=7 supervisor uv
cd "$ROOT/app/backend"
"$ROOT/runtime/bin/uv" sync --frozen --no-dev --python "$ROOT/runtime/bin/python"
"$ROOT/runtime/bin/python" "$ROOT/app/scripts/server_service.py" setup --host 127.0.0.1
```

默认只绑定本机。通过 SSH 隧道或自行配置的 HTTPS 反向代理访问；公开部署前完善访问控制、TLS 和允许的来源。PostgreSQL/Redis 仅监听本机并使用随机凭证。

`setup` 会初始化独立数据目录、生成私有凭证、迁移数据库、启动四个服务，并添加当前用户的 `@reboot` 条目；保留其他已有条目。已有数据和凭证会复用。

## 运维

```bash
ROOT="$HOME/apps/narrative-ppt"
"$ROOT/runtime/bin/python" "$ROOT/app/scripts/server_service.py" status
"$ROOT/runtime/bin/python" "$ROOT/app/scripts/server_service.py" stop
"$ROOT/runtime/bin/python" "$ROOT/app/scripts/server_service.py" start
```

更新前备份数据库、上传文件和私有配置；停止 API / worker 后更新代码、同步锁定依赖、执行迁移再启动。不要删除 `data/` 或重新生成已有 `secrets.json`。模型配置变更后需重新执行 setup，保留原有加密密钥。不要在 issue 中粘贴原始配置或日志。

## 已验收范围

2026-10-04 完成上传、生成、导出、进程重启后持久化验证。2026-10-06 部署长页数修复，默认模型 `DMXAPI-deepseek-v4-flash`、读取等待 180 秒；5/10/15/20 页真实模型生成和导出均通过。具体耗时、质量提示与历史失败见 [最新报告](LONG_OUTLINE_FIX.md)。

Supervisor 子进程恢复和启动入口已配置；尚未实测整台共享服务器重启、并发压测、公网 TLS 或长期运行 SLA。仓库中的 Docker Compose 生产配置不是本次部署验收的路径，应单独验证。
