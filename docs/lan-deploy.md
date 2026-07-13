# Windows 单机内网试用部署

本方案用于在一台 Windows 电脑上运行 LIMS MVP，供同一可信内网中的少量试用用户访问。
前端通过 `5173` 提供页面，后端通过 `18000` 提供 API；PostgreSQL 仅绑定部署机回环地址，
不作为内网用户入口。本方案不是公网或正式生产部署方案。

## 部署前提

- Windows 10/11 或 Windows Server，并已安装 PowerShell 7（`pwsh.exe`）。
- 已安装并启动 Docker Desktop，`docker compose version` 可正常执行。
- 已安装 Node.js，`npm.cmd --version` 可正常执行。
- 已安装 Python 3.12，并已执行 `.\scripts\setup-backend.ps1`。
- 部署机使用稳定的内网 IPv4 地址；建议在路由器或网卡上固定地址。
- 已按实际环境修改密码和 `SECRET_KEY`。试用网络应为可信内网，不要直接映射到公网。

使用 `ipconfig` 找到部署机网卡的 IPv4 地址，例如 `192.168.3.50`。不要填写
`0.0.0.0`，也不要填写其他电脑的地址。

## 启动

在仓库根目录执行：

```powershell
.\scripts\start-lan-demo.ps1 -HostIP 192.168.3.50
```

脚本执行以下操作：

1. 启动 PostgreSQL 容器，宿主机端口保持 `127.0.0.1:15432`。
2. 运行 Alembic 迁移并启动后端，监听 `0.0.0.0:18000`。
3. 启动 Vite 前端，监听 `0.0.0.0:5173`。
4. 临时设置 `VITE_API_BASE_URL=http://192.168.3.50:18000/api`。
5. 临时把 `http://192.168.3.50:5173` 加入后端 `CORS_ORIGINS`。

启动器会保留 `.env` 中的数据库账号、密码和库名，并在当前进程内把数据库主机名
`localhost:15432` 规范化为 `127.0.0.1:15432`，避免部分 Windows 环境中的名称解析等待。

这些内网变量仅对脚本启动的进程有效，不会改写 `.env`。脚本会打开两个服务终端；
关闭相应终端即可停止前端或后端。

## Windows 防火墙

仅需为当前内网配置文件放行入站 TCP：

- `5173`：LIMS 前端
- `18000`：LIMS 后端 API

不要为 `15432`（PostgreSQL）或 MinIO 的 `9000/9001` 创建内网入站规则。本仓库当前
Compose 没有启动 MinIO；如果以后启用，也应保持仅部署机或后端网络可访问。

可在“Windows Defender 防火墙（高级安全）”中创建两个入站规则，并把“配置文件”
限制为“专用”，远程 IP 范围限制为实际办公网段。不要关闭整个 Windows 防火墙。

## 验证步骤

部署机上执行：

```powershell
Invoke-RestMethod http://127.0.0.1:18000/api/health
Test-NetConnection 127.0.0.1 -Port 5173
Test-NetConnection 127.0.0.1 -Port 18000
Test-NetConnection 127.0.0.1 -Port 15432
```

另一台同内网电脑上：

1. 浏览器打开 `http://192.168.3.50:5173`。
2. 使用 demo 账号登录并打开项目、实验或库存列表。
3. 浏览器开发者工具中确认 API 请求发往
   `http://192.168.3.50:18000/api`，且没有 CORS 错误。
4. 可执行 `Test-NetConnection 192.168.3.50 -Port 5173` 和
   `Test-NetConnection 192.168.3.50 -Port 18000`。
5. `Test-NetConnection 192.168.3.50 -Port 15432` 应失败；数据库不应暴露到内网。

## 常见错误

### 页面无法打开

- 确认 `HostIP` 是部署机当前 IPv4 地址，而不是 Wi-Fi Direct、虚拟网卡或 VPN 地址。
- 确认前端终端仍在运行，并检查 `5173` 是否被其他进程占用。
- 检查客户端与部署机是否在可互通网段，以及防火墙规则是否限定到了错误的配置文件或网段。

### 页面能打开，但 API 请求失败

- 确认后端终端没有迁移或启动错误。
- 浏览器请求地址必须是 `http://<HostIP>:18000/api`，不能是客户端自己的
  `127.0.0.1`。
- 如果手动启动后端，`CORS_ORIGINS` 必须精确包含 `http://<HostIP>:5173`；
  Origin 不包含路径，末尾不要添加 `/`。

### 端口被占用

```powershell
Get-NetTCPConnection -LocalPort 5173,18000,15432 -ErrorAction SilentlyContinue
```

停止占用端口的旧 LIMS 进程或容器后重新运行脚本。本试用方案固定使用这些端口，
不建议临时改端口造成前后端配置不一致。

### Docker 或数据库启动失败

确认 Docker Desktop 已启动，再运行：

```powershell
docker compose ps
docker compose logs postgres
```

若数据库尚未就绪，等待健康检查通过后重新启动后端。不要删除数据卷来处理普通启动错误。

## 停止与回滚

1. 在前端和后端终端中按 `Ctrl+C`，然后关闭终端。
2. 停止 PostgreSQL 容器但保留数据：

   ```powershell
   docker compose stop postgres
   ```

3. 恢复为仅本机开发时，按 README 的 `start-backend.ps1` 和
   `start-frontend.ps1` 启动；内网变量没有写入 `.env`，无需清理。
4. 若要撤销本次部署配置，恢复 `docker-compose.yml`、环境模板、README 和脚本/文档。

不要执行 `docker compose down -v`，除非已经备份且明确要永久删除 PostgreSQL 数据。
