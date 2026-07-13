# LIMS 全栈 MVP（lims-fullstack-mvp）

实验室信息管理系统 MVP。前端(React + TypeScript + antd / Ant Design Pro)+ 后端(FastAPI + SQLAlchemy + Alembic + PostgreSQL),合流为单仓库。来源 commit 见 `docs/INTEGRATION_BASELINE.md`。

## 技术栈与端口

| 组件 | 技术 | 地址 |
|---|---|---|
| 数据库 | PostgreSQL 15（docker-compose）| `localhost:15432` |
| 后端 | FastAPI | `http://127.0.0.1:18000/api` |
| 前端 | Vite dev | `http://localhost:5173` |

响应统一 `{ code, message, data }`,分页 `{ items, total, page, page_size }`。

## 从零启动（Windows PowerShell）

```powershell
# 0) 环境模板（脚本会自动复制；也可手动）
Copy-Item .env.example backend\.env
Copy-Item .env.example frontend\.env

# 1) 启动数据库（PostgreSQL，端口 15432）
.\scripts\start-db.ps1

# 2) 后端：建虚拟环境 + 安装依赖 + 迁移 + demo seed
.\scripts\setup-backend.ps1

# 3) 启动后端（127.0.0.1:18000）
.\scripts\start-backend.ps1

# 4) 另开一个终端，启动前端（5173，real 模式连后端）
.\scripts\start-frontend.ps1

# 5) 全栈验证（前端三检+单测、后端 compileall+pytest、全栈 smoke）
.\scripts\verify-fullstack.ps1
```

## 内网试用部署

在一台 Windows 电脑上向同一内网开放 LIMS 前端和 API：

```powershell
.\scripts\start-lan-demo.ps1 -HostIP 192.168.3.50
```

部署前提、防火墙配置、验证、常见错误和回滚步骤见
[`docs/lan-deploy.md`](docs/lan-deploy.md)。PostgreSQL 保持仅部署机本地可访问，
普通内网用户只需访问前端 `5173` 端口。

## API 模式

- `frontend/.env` 的 `VITE_API_MODE=real` → 连真实后端(`VITE_API_BASE_URL`)。
- `VITE_API_MODE=mock` → 使用前端内置 mock,不请求后端(离线演示用)。

## 测试账号（demo seed,默认密码 `password123`）

标准角色为 `admin` / `director` / `project_manager` / `operator`。
中文名称分别为“系统管理员”/“主管”/“项目负责人”/“操作员”。演示账号使用规范用户名 `project_manager`；历史角色值 `pm` 仍可归一为 `project_manager`，但不再单独提供 `pm` 演示账号。

需要重建干净、可重复的本地演示环境时，请使用受保护的 `.\scripts\seed-demo.ps1 -Force`。账号、数据摘要和按角色浏览器验收路径见 [`docs/demo-walkthrough.md`](docs/demo-walkthrough.md)。

## 账号发放

系统不开放自助注册，也不提供公开注册页。内网部署后的账号由系统管理员登录后，
在“管理员管理”页面点击“添加账号”创建。管理员需设置用户名、显示名、初始密码、
角色和启用状态；新账号首次登录后必须修改初始密码。非管理员无法看到用户管理入口，
也无权调用管理员创建账号接口。

## 手动命令（不走脚本时）

后端(在 `backend/`,已激活 `.venv`):
```powershell
python -m alembic upgrade head
python scripts\seed_demo.py
python -m uvicorn app.main:app --port 18000 --reload
$env:TEST_DATABASE_URL="sqlite+pysqlite:///:memory:"; python -m pytest -q
```

前端(在 `frontend/`):
```powershell
npm install
npm run typecheck; npm run lint; npm run test; npm run build
npm run dev
```

## 非阻塞遗留（见 docs/INTEGRATION_BASELINE.md 与各模块说明）

- 当前 MVP 已包含附件真实上传、列表、下载和删除，以及管理后台用户管理、审计日志列表和实体详情审计时间线。
- T1.4 已完成实验扩展字段、日报多条 items UI、确认出库和实验来源库存流水。
- T1.4 词表、接口和权限见 `docs/T1.4_BUSINESS_FLOWS.md`。
- T1.5 已完成样品、检测任务、结果录入与审核/退回真实闭环，见 `docs/T1.5_LIMS_MAIN_CHAIN.md`。
- 当前附件使用受控的本地存储实现；AI 日报、周报统计、扫码/条码和全局搜索仍为后续范围。
