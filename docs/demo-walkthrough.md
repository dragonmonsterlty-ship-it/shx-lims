# T1.10 本地 Demo Seed 与浏览器验收

本流程仅用于本地 demo/dev，不得用于生产环境。重置脚本会删除并重建当前后端配置指向的数据库结构和全部数据。

## 1. 重建演示数据

关闭正在访问数据库的后端进程，在仓库根目录执行：

```powershell
Set-Location D:\vibecoding\lims-fullstack-mvp
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\seed-demo.ps1 -Force
```

脚本只允许 PostgreSQL、`localhost`/`127.0.0.1`、端口 `15432`，并要求数据库名为默认本地库 `lims` 或明确包含 `demo`/`dev`/`test`。不带 `-Force` 时只显示破坏性警告并中止。

`npm.cmd run verify:api` 会生成带时间戳的额外验证数据。正式演示前应再次执行上述 seed 命令恢复干净数据。

## 2. 启动服务

分别打开两个 PowerShell 终端：

```powershell
Set-Location D:\vibecoding\lims-fullstack-mvp
.\scripts\start-backend.ps1
```

```powershell
Set-Location D:\vibecoding\lims-fullstack-mvp
.\scripts\start-frontend.ps1
```

前端地址为 `http://localhost:5173`，后端 API 为 `http://127.0.0.1:18000/api`。

## 3. 演示账号

所有账号默认密码均为 `password123`。

| 用户名 | 角色 | 可访问模块 | 用途 |
|---|---|---|---|
| `admin` | admin | `lims`、`refstd` | 用户管理、全局审计与实体时间线 |
| `project_manager` | project_manager | `lims` | 管理项目 A/B，审核日报与检测结果 |
| `analyst` | operator | `lims` | 执行项目 A 中分配给自己的检测任务 |
| `operator` | operator | `lims` | 创建/查看项目 A 的实验和日报 |
| `qc_operator` | operator | 仅 `refstd` | QC 对照品工作区演示账号 |

项目 A 为 `MVP Demo Project A`，包含完整演示链。项目 B 为 `MVP Demo Project B`，仅项目负责人可访问，用于验证 analyst/operator 的跨项目隔离。

## 4. 演示数据摘要

- 实验：一条草稿实验、一条已提交实验；标题、目的、步骤、结果摘要均可读。
- 日报：一条包含两个事项的草稿日报、一条已确认日报。
- 样品：`DEMO-SAMPLE-PENDING` 为待处理检测样品；`DEMO-SAMPLE-COMPLETE` 为已完成样品。
- 检测：一条待开始任务；另一条已沿 `pending → in_progress → submitted → approved` 流程完成。
- 审计：实验、日报、样品及检测流程均由现有 service 产生真实审计事件。
- 附件：seed 不写入虚假附件记录；演示时人工上传一个小型 `.txt` 或 `.csv` 文件。

## 5. 按角色验收

### admin

1. 使用 `admin` 登录，打开用户管理，确认演示账号均为启用状态。
2. 打开审计日志，确认可查看全局创建、提交、审核等事件。
3. 分别打开实验、日报、样品详情，确认实体审计时间线可见。
4. 在样品详情上传一个小型 `.txt` 文件，依次验证列表、下载和删除。

### project_manager

1. 使用 `project_manager` 登录，确认可看到本人负责的项目 A 和项目 B。
2. 打开项目 A，查看草稿/已提交实验和草稿/已确认日报。
3. 查看两个演示样品以及待处理、已完成检测任务。
4. 打开审计日志，确认只显示本人管理项目范围内的数据。
5. 在样品详情查看时间线，并人工验证小型附件上传、下载、删除。

### analyst

1. 使用 `analyst` 登录，查看分配给自己的检测任务。
2. 对 `DEMO-SAMPLE-PENDING` 的待处理任务执行“开始”，录入结果并提交；如需演示批准，再切换 `project_manager` 完成审核。
3. 直接访问 `/admin/users`，确认被拒绝或跳转到无权限页面。
4. 直接访问 `/audit-logs`，确认被拒绝或跳转到无权限页面。
5. 尝试访问项目 B 或其实体，确认列表不可见且直接访问被拒绝。

### operator

1. 使用 `operator` 登录，查看项目 A 的实验与日报。
2. 确认项目 B 不在可访问范围内。
3. 打开项目 A 的实验、日报和样品详情，确认仅能执行角色允许的操作。

## 6. 演示结束后的注意事项

- 附件文件存储为受控的本地开发存储，演示结束后可随数据库一并重新 seed。
- 不要将本脚本用于共享、测试以外或生产数据库。
- 若脚本的主机、端口或数据库名保护校验失败，应检查 `backend/.env`，不要绕过保护。
