# T1.2 Frontend API Integration Design

## 目标与边界

仅修改 `D:\vibecoding\lims-frontend-mvp`，将现有 React 页面从固定 mock 数据源切换为可配置的真实后端 API。默认使用 `VITE_API_MODE=real` 与 `VITE_API_BASE_URL=http://127.0.0.1:18000/api`。后端仓库只读，不改契约、不正式合流、不重做 UI。

## 架构

- `src/api/http.ts` 负责 Axios、Bearer token、统一响应信封和错误归一化。
- `src/api/runtime.ts` 负责 `real/mock` 模式判定，两个模式不共享业务状态，也不做隐式 fallback。
- `src/api/adapters.ts` 将 T1.1 后端模型映射为现有页面模型，避免页面直接理解后端兼容字段。
- `src/services/*` 作为唯一数据入口：real 模式调用 HTTP，mock 模式调用原 mock server。
- 页面继续使用 React Query、ProTable 与现有布局，只补充真实负责人候选、错误提示和后端缺失字段兼容显示。

## 数据流

1. 登录在 real 模式调用 `/auth/login`，保存 access/refresh token 与用户。
2. 请求拦截器附加 `Authorization: Bearer <token>`。
3. `request()` 解包 `{code,message,data}`；`code !== 0` 或 HTTP 4xx/5xx 转为统一 `ApiError`。
4. 列表服务返回 `{items,total,page,page_size}`。
5. 项目、实验、日报、试剂库存通过纯适配函数转成现有 UI 类型。

## 兼容策略

- 项目列表的 `code/type/owner/expected_end_date` 映射为页面使用的 `project_code/project_type/lead_user_id/end_date`。
- 实验记录的 `code/owner/procedure/reagent_usages` 映射为现有实验页面字段；真实后端没有参与人和计划区间时使用空数组或实验日期。
- 日报列表缺少具体项目 ID 与明细内容时显示摘要和空占位；详情使用第一条 item 映射现有单项目/单实验 UI。
- 库存列表组合 `/reagent-lots` 与 `/reagents`；详情组合 lot、reagent 与 `/inventory-transactions`。
- 后端没有的删除、冻结、实验物料确认出库等操作在 real 模式明确报“当前后端契约暂不支持”，绝不回退到 mock。

## 错误与状态

- 网络失败显示“无法连接后端 API，请检查服务地址或服务状态”。
- 401/403/404/400/409/422 保留后端 message；422 提取字段错误。
- 详情页沿用 `QueryBoundary`；列表页捕获请求错误并显示可见 Alert。
- ProTable/QueryBoundary 保留 loading 和 empty state。

## 测试与验收

- 使用 Vitest 测试模式选择、信封解包、错误归一化和关键字段适配。
- 运行 `npm run test`、`npm run typecheck`、`npm run lint`、`npm run build`。
- 若 `127.0.0.1:18000` 可用，使用真实登录 token 验证 health、项目列表/详情、负责人候选、实验、日报和试剂批次；负责人候选不得包含普通角色。
- 所有后端契约差异只写入前端验收报告，不改后端。
