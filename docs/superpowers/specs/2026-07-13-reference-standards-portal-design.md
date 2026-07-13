# 对照品管理与双工作区门户设计

## 目标与边界

为 QC/QA 部门新增对照品管理模块，与现有合成实验室功能在同一系统内并存。
登录后进入门户页，通过两张大卡片选择进入"实验室管理"或"对照品管理"工作区。
合成部门负责对照品入库，QC/QA 负责领用与消耗登记。

本期范围：

- 门户页与双工作区框架，用户级模块授权。
- 对照品台账：入库、编辑、报废、效期字段与列表临期/过期高亮。
- 领用/消耗流水：登记即领（无审批环节），余量自动扣减。
- COA 等附件复用现有附件机制；全部写操作进现有审计日志。

明确不做：效期复验流程、到期主动提醒、领用审批流、条码/扫码。

## 现状

- `User` 模型已有 `department`（可空自由文本）与六种角色
  （`admin`/`director`/`project_manager`/`researcher`/`operator`/`viewer`）。
- 前端菜单为 `layouts/menu.ts` 中按角色过滤的扁平列表；路由在 `router/index.tsx`，
  所有已登录页面挂在单一 `AppLayout` 下的根路径（`/dashboard`、`/samples` 等）。
- 附件通过 `services/attachment_entities.py` 按实体类型解析权限；
  审计日志支持任意 `action`/`entity_type`。
- 登录成功后跳 `/dashboard`。

## 模块授权模型

用户新增 `modules` 字段（`String(100)`，逗号分隔，如 `"lims,refstd"`）：

- `lims`：合成实验室工作区（现有全部功能）。
- `refstd`：对照品管理工作区。
- Alembic 迁移为存量用户回填 `"lims"`；`admin` 角色无视该字段，视为拥有全部模块。
- 模块决定"能进哪个工作区"；角色决定"工作区内能做什么"，两者正交。
- 前端按模块渲染门户卡片和路由守卫；**后端在对照品所有 API 上同步校验模块**，
  不依赖前端拦截。
- 管理员建号/管理页面新增"可访问模块"多选（默认仅 `lims`）。

对照品模块内的动作权限（首版）：

| 动作 | 要求 |
|---|---|
| 查看台账、流水、详情 | 拥有 `refstd` 模块 |
| 入库、编辑、报废 | `refstd` 模块且角色非 `viewer` |
| 领用/消耗登记 | `refstd` 模块且角色非 `viewer` |

"仅合成可入库"首版作为操作约定（审计日志可追责），不做系统硬限制；
若需强制，规范化 `department` 取值后在服务层加一条校验即可（见待确认项）。

## 数据模型

新表 `ref_standard`（对照品台账）：

- `id`、`code`（对照品编号，唯一，非空）、`name`（非空）
- `batch_no`（批号）、`source`（`self_made`/`purchased`）
- `spec`（规格）、`assigned_value`（标定值/纯度描述，文本）
- `initial_amount`/`current_amount`（`Numeric(18,4)`）、`unit`
- `storage_condition`、`expires_at`（`Date`，可空）
- `status`（`in_stock`/`depleted`/`disposed`），`notes`
- `created_by`（FK user）、`created_at`/`updated_at`、`is_deleted` 软删除
  （与现有业务表约定一致）

新表 `ref_standard_usage`（领用/消耗流水，只增不改）：

- `id`、`ref_standard_id`（FK）、`used_by`（FK user）
- `amount`（`Numeric(18,4)`）、`unit`、`used_at`、`purpose`（用途/备注）
- `created_at`

领用登记与余量扣减在同一事务完成：`current_amount -= amount`，
不足时返回 400 并提示当前余量；扣减至 0 时状态自动置 `depleted`。
过期不改状态字段，由 `expires_at` 即时判断（列表/详情标红），避免状态与日期不一致。

## 后端设计

新路由 `backend/app/api/ref_standards.py`，前缀 `/api/ref-standards`：

- `GET /` 列表：分页 + 按 `code`/`name`/`batch_no`/`status` 过滤，
  支持 `expiring_within_days` 查询临期。
- `POST /` 入库；`code` 重复返回 409。
- `GET /{id}` 详情；`PATCH /{id}` 编辑；`POST /{id}/dispose` 报废。
- `GET /{id}/usages` 流水列表；`POST /{id}/usages` 领用登记。

服务层 `services/ref_standards.py` 统一执行模块校验（`ensure_refstd_module`，
参照 `ensure_admin_user` 的写法）。审计动作：`create`/`update`/`dispose`/`use`，
`entity_type=ref_standard`。附件：在 `attachment_entities.py` 注册 `ref_standard`
实体（COA、图谱挂详情页）。

## 前端设计

**门户页** `/portal`（新 `pages/portal/PortalPage.tsx`，不套 `AppLayout`）：

- 两张大卡片：实验室管理（`SketchIcon flask` 角标）、对照品管理（`test-tube` 角标），
  米白背景，与登录页风格连续；卡片交互与文字保持 AntD 干净观感。
  门户属视觉宪法"看一眼"白名单区域。
- 按 `modules` 渲染卡片；仅有一个模块时直接重定向进该工作区。
- 登录成功后跳 `/portal`（原 `/dashboard` 跳转改这里）；`/` 根路径同。

**对照品工作区**：新增 `RefStdLayout`（第二个 ProLayout 实例，独立菜单）：

- 路由 `/ref-standards`（列表）、`/ref-standards/:id`（详情）。
- 菜单首版仅"对照品台账"一项；顶栏用户菜单加"返回门户"。
- 现有实验室工作区路由**保持原路径不动**（`/dashboard`、`/samples` 等），
  仅将其菜单归入 lims 工作区语义，避免大范围路由迁移与回归风险。
  实验室工作区顶栏同样加"返回门户"。

**页面**：

- 列表页：ProTable，列含编号/名称/批号/余量/效期/状态；效期临期（30 天内）
  黄色 Tag、已过期红色 Tag；工具栏"入库登记"主按钮（Modal + Form）。
  空状态用 `<SketchEmpty description="暂无对照品" />`。
- 详情页：基本信息 + 余量卡片 + 领用流水表（内嵌"领用登记"按钮与 Modal）
  + 复用现有附件面板。
- 路由守卫：新增 `ModuleGuard`（参照 `RoleGuard`），无 `refstd` 模块访问
  `/ref-standards/*` 时跳 403。

**管理员管理页**：用户列表加"可访问模块"列；建号与编辑支持模块多选。

## 测试与验证

- 后端：模块校验（无 `refstd` 模块 403）、入库/编辑/报废契约、`code` 重复 409、
  领用扣减与超余量 400、扣至 0 自动 `depleted`、审计行内容、附件实体解析。
- 前端：服务层契约测试；列表/入库/领用交互测试（沿用 Vitest + Testing Library）；
  门户卡片按模块渲染与单模块重定向测试；`ModuleGuard` 测试。
- 完成后运行后端完整 pytest、前端 test/typecheck/lint/build、
  `scripts/verify-fullstack.ps1`，并更新 demo seed（增加 QC 演示账号与示例对照品）。

## 里程碑

- **M1 门户与授权骨架**：`modules` 字段与迁移、门户页、双工作区布局与守卫、
  管理员页模块多选。不含对照品业务，可独立验收。
- **M2 对照品台账**：数据表、入库/编辑/报废、列表/详情、附件、审计。
  验收标准：合成账号可入库并挂 COA，QC 账号可查询。
- **M3 领用闭环**：流水表、领用登记、余量扣减、效期高亮、demo seed 与文档。
  验收标准：QC 账号完成一次领用，余量与流水正确，审计可查。

## 待确认项

1. 对照品编号 `code` 的规则：管理员手填，还是系统按规则生成（如 `RS-2026-001`）？
   首版按手填 + 唯一校验设计。
2. 是否需要系统硬性限制"仅合成部门可入库"（需先规范 `department` 取值）。
3. QC/QA 新账号建议使用 `operator` 角色 + 仅 `refstd` 模块；只读账号用 `viewer`。
4. 领用登记的 `used_by` 默认为当前登录人；是否需要支持代他人登记？首版不支持。
