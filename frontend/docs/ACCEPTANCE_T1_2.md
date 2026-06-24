# T1.2 Frontend API Integration 验收

## 结论

T1.2 已完成：前端默认 real 模式接入 T1.1 后端 JWT、统一响应信封和分页，项目、实验、日报、试剂库存的列表/详情已通过真实后端与浏览器验证。未进入 T1.3，未做正式合流，后端仓库无文件改动。

## 配置

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:18000/api
VITE_API_MODE=real
```

切换 mock：

```dotenv
VITE_API_MODE=mock
```

real 与 mock 不做隐式混用或 fallback。

## 接入范围

- 认证：登录、Bearer token、本地会话、登出、当前用户。
- health：`healthService.checkHealth()` 与 `npm run verify:api`。
- 项目：列表、详情、分页、关键字/状态/类型/负责人/优先级筛选、成员、负责人候选。
- 实验记录：列表、详情、附件元数据、试剂使用元数据。
- 日报：列表、详情、创建/更新/提交/审核/退回、附件元数据。
- 库存：试剂、批次、组合列表、批次详情、库存流水、入库与调整。
- 页面状态：列表 loading/empty 由 ProTable 提供；列表错误显示 Alert；详情使用 QueryBoundary；网络错误显示“无法连接后端 API，请检查服务地址或服务状态”。

## 验证结果

| 检查 | 结果 |
|---|---|
| `npm.cmd run test` | 通过，3 个测试文件、11 个测试 |
| `npm.cmd run typecheck` | 通过 |
| `npm.cmd run lint` | 通过 |
| `npm.cmd run build` | 通过，4214 modules transformed |
| `npm.cmd run verify:api` | 通过 |
| 官方 `backend/scripts/smoke_api.py` | 通过 |
| 浏览器真实登录 | 通过，`admin/password123` |
| 项目列表/详情 | 通过，2 条项目 |
| 负责人候选角色排除 | 通过，仅 `admin/pm/project_manager`，无 operator/researcher/analyst/qa |
| 实验列表/详情 | 通过，2 条实验 |
| 日报列表/详情 | 通过，2 条日报 |
| 试剂/批次列表与批次详情 | 通过，2 个试剂、2 个批次 |
| 后端仓库 Git 状态 | 干净 |

## 后端契约问题与限制

1. `API_CONTRACT.md` 说明 `director` 为只读、不可审核；但后端 `DAILY_REPORT_REVIEW_ROLES` 包含 `director`，实际实现允许其审核日报。前端未修改后端，仅记录。
2. `GET /api/users` 存在于 OpenAPI 与运行代码，但 `API_CONTRACT.md` 的用户接口说明未列出该端点。前端用它解析用户姓名，负责人下拉仍严格使用 `/users/project-owner-candidates`。
3. 日报列表响应只含摘要与数量，不含具体 `project_id`、`experiment_record_id` 和 item 内容；因此列表页兼容显示摘要，项目/实验列显示 `—`，详情页再展示真实关联。
4. 后端实验写入要求 `code` 与 `record_type`，与当前前端实验表单（编号可空、无 record_type）不一致。本轮按目标只接入真实读取，real 模式隐藏实验新增/编辑/删除/直接物料出库操作。
5. 后端没有批次冻结/解冻、实验关联批次反查端点；real 模式不回退 mock，相关 unsupported 操作隐藏或返回明确错误。

## 遗留问题

- 完成实验与日报写入模型的正式 UI 对齐属于后续任务，不在 T1.2 读取联调范围。
- 日报列表若需直接显示项目/实验，应由后端补充列表字段，或后续确认是否接受 N+1 详情请求。
- 浏览器控制台仍有 React Router v7 future flag 与 Ant Design Pro `findDOMNode` 依赖级弃用警告；无 API 错误或运行时崩溃。
- 真实附件上传/下载、图谱解析不在后端 T1.1 契约支持范围。

本轮停在 `T1.2-frontend-api-integration`。
