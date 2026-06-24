# T1.2 Frontend API Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 默认 real 模式下让现有 LIMS 前端通过统一 API client 读取并展示 T1.1 后端的项目、负责人候选、实验、日报和库存数据。

**Architecture:** 保留现有页面和 UI 类型，在 `src/api` 增加运行模式与纯适配层，各 `src/services` 根据模式选择 HTTP 或 mock。真实模式不隐式回退，后端未提供的操作返回统一可见错误。

**Tech Stack:** React 18、TypeScript、React Query、Axios、Ant Design Pro、Vitest。

---

### Task 1: 测试基础设施与 API 核心

**Files:**
- Modify: `package.json`
- Modify: `src/api/client.ts`
- Modify: `src/api/http.ts`
- Modify: `src/api/errors.ts`
- Create: `src/api/runtime.ts`
- Test: `src/api/client.test.ts`
- Test: `src/api/errors.test.ts`

- [ ] 添加 Vitest 与 `npm run test`。
- [ ] 先写失败测试，覆盖默认 real、显式 mock、信封解包、网络错误和 HTTP 错误。
- [ ] 实现最小模式选择与统一错误处理。
- [ ] 运行 API 核心测试并确认通过。

### Task 2: 后端字段适配

**Files:**
- Create: `src/api/adapters.ts`
- Modify: `src/types/auth.ts`
- Modify: `src/types/project.ts`
- Modify: `src/types/experiment.ts`
- Modify: `src/types/dailyReport.ts`
- Modify: `src/types/inventory.ts`
- Test: `src/api/adapters.test.ts`

- [ ] 先写失败测试，覆盖项目、实验、日报、试剂批次和库存流水映射。
- [ ] 补充后端 read model 与兼容 UI 类型。
- [ ] 实现纯适配函数并运行测试。

### Task 3: 认证、health、用户和项目

**Files:**
- Modify: `src/api/endpoints.ts`
- Modify: `src/services/auth.ts`
- Create: `src/services/health.ts`
- Modify: `src/services/user.ts`
- Modify: `src/services/project.ts`
- Modify: `src/services/index.ts`
- Modify: `src/pages/auth/LoginPage.tsx`
- Modify: `src/pages/projects/ProjectListPage.tsx`
- Modify: `src/pages/projects/ProjectFormModal.tsx`

- [ ] 接入真实登录、登出、本人与 health。
- [ ] 项目列表/详情使用真实分页和筛选参数。
- [ ] 负责人候选只调用 `/users/project-owner-candidates`。
- [ ] 项目列表增加可见错误提示。

### Task 4: 实验、日报与库存读取

**Files:**
- Modify: `src/services/experiment.ts`
- Modify: `src/services/dailyReport.ts`
- Modify: `src/services/inventory.ts`
- Modify: `src/pages/experiments/ExperimentListPage.tsx`
- Modify: `src/pages/experiments/ExperimentDetailPage.tsx`
- Modify: `src/pages/dailyReports/DailyReportListPage.tsx`
- Modify: `src/pages/dailyReports/DailyReportDetailPage.tsx`
- Modify: `src/pages/inventory/InventoryListPage.tsx`
- Modify: `src/pages/inventory/InventoryDetailPage.tsx`
- Modify: `src/components/status.ts`

- [ ] 实验列表/详情映射真实 `/experiment-records`。
- [ ] 日报列表/详情映射真实 `/daily-reports`。
- [ ] 库存列表/详情组合 reagent、lot、transaction 接口。
- [ ] 列表增加错误提示，缺失字段显示占位而不崩溃。
- [ ] 后端缺失操作明确报错，不调用 mock。

### Task 5: 环境、文档与验证

**Files:**
- Create: `.env.example`
- Modify: `README.md`
- Create: `docs/ACCEPTANCE_T1_2.md`

- [ ] 写明 API 地址、real/mock 切换与常见问题。
- [ ] 运行 `npm run test`、`npm run typecheck`、`npm run lint`、`npm run build`。
- [ ] 对可用的 18000 后端执行真实 API smoke；记录不可用或契约差异。
- [ ] 检查后端仓库无改动，前端 diff 无越界。
- [ ] 提交 `T1.2 frontend integrate real backend API`。
