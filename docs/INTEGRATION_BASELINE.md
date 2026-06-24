# 合流基线（INTEGRATION_BASELINE）

本仓库 `lims-fullstack-mvp` 由前端与后端两个独立仓库合流而成,作为可启动、可验收的全栈 MVP。

## 来源 commit

| 子目录 | 源仓库 | 源 commit |
|---|---|---|
| `frontend/` | `D:\vibecoding\lims-frontend-mvp`(其 `frontend/` 应用) | `e539207 fix(frontend): align daily report items with backend contract` |
| `backend/` | `D:\vibecoding\lims-backend-reagent`(其 `backend/` 应用) | `593f3b2 T1.1 backend harden local integration setup` |

合流方式:仅复制源码,**不嵌套 `.git`**(各源仓库的 `.git` 未带入);依赖(`node_modules`/`.venv`)与缓存(`__pycache__`/`.pytest_cache`)、本地 `.env`、`*.db` 均未带入,由脚本在本地重建。

## 目录结构

```
lims-fullstack-mvp/
├─ frontend/                # React + TS + antd（Vite），源自前端仓库
├─ backend/                 # FastAPI + SQLAlchemy + Alembic，源自后端仓库
├─ docker-compose.yml       # 仅 PostgreSQL（宿主机端口 15432）
├─ .env.example             # 前后端合并环境模板
├─ scripts/                 # Windows PowerShell 启动/验证脚本
├─ docs/INTEGRATION_BASELINE.md
└─ README.md
```

## 合流边界（本轮 T1.3）

- 不改后端业务逻辑,不改前端业务功能,不新增模块。
- 不做附件真实上传、AI 日报、出库扣减、8 类物料重构。
- 仅做合流、环境、脚本、README、全栈验收。

## 契约要点（前后端对齐,详见各自文档）

- 统一响应信封 `{ code, message, data }`,分页 `{ items, total, page, page_size }`。
- 前端 real 模式经 `frontend/src/api/adapters.ts` 适配后端字段(项目 code/owner、实验 experiment-records、日报 items[]、试剂 reagents/reagent-lots)。
- 角色词表归一:后端 `pm/researcher` 等 → 前端 `project_manager/operator`。
- 已知非阻塞差异见 README「非阻塞遗留」。
