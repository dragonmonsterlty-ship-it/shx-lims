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

## API 模式

- `frontend/.env` 的 `VITE_API_MODE=real` → 连真实后端(`VITE_API_BASE_URL`)。
- `VITE_API_MODE=mock` → 使用前端内置 mock,不请求后端(离线演示用)。

## 测试账号（demo seed,默认密码 `password123`）

标准角色为 `admin` / `director` / `project_manager` / `operator`。
中文名称分别为“系统管理员”/“主管”/“项目负责人”/“操作员”。演示账号使用规范用户名 `project_manager`；历史角色值 `pm` 仍可归一为 `project_manager`，但不再单独提供 `pm` 演示账号。

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

- 附件真实上传、出库扣减/dispense、8 类物料、AI 日报、周报统计:未实现(mock-only 或后续)。
- T1.4 已完成实验扩展字段、日报多条 items UI、确认出库和实验来源库存流水。
- T1.4 词表、接口和权限见 `docs/T1.4_BUSINESS_FLOWS.md`。
- 附件对象存储、样品/检测/结果审核、AI 日报与周报统计留待 T1.5+。
