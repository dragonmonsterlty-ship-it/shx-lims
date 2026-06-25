# 前端 API 契约（API_CONTRACT_FRONTEND）

> 本文档描述**前端期望的接口契约**，用于 T1.1 前后端合流。当前所有数据走 `src/services/*`
> → `src/api/mock`（mock adapter）。切真实后端时把 service 内的 mock 调用替换为
> `http.request(endpoints.*)`（见 `src/api/http.ts` / `src/api/endpoints.ts`），契约保持不变。

## 通用约定

- **基址**：`VITE_API_BASE_URL`（默认 `http://localhost:8000/api`）。
- **响应信封**：`{ code: number, message: string, data: T }`，`code===0` 成功；否则 `message` 为错误文案。
- **分页**：`{ items: T[], total: number, page: number, page_size: number }`。
- **鉴权**：`Authorization: Bearer <access_token>`；401 触发 refresh（mock 不强依赖）。
- **字段命名**：snake_case，与本文件类型一致（前端 `src/types`）。
- **错误码**：`401` 未登录/凭证失效、`403` 越权、`404` 不存在、`409` 唯一冲突、`422` 校验失败、`0` 成功。

## 后端实现状态

| 模块 | 后端 | 说明 |
|---|---|---|
| Auth / Users | ✅ 已实现 | `/auth/*`、`/users/me` |
| Projects / Members | ✅ 已实现 | `/projects*`；**列表返回纯数组**，前端 `toPageResult` 归一 |
| DailyReports(日报) | ⚠️ 部分/待对齐 | 后端为 `daily_log`(单 content)；前端为拆分字段 `daily_report`，需后端对齐 |
| Attachments | ✅ 上传/下载/列表 | 无删除、无缩略图端点 |
| Experiments + 物料使用 | ❌ mock-only | 后端尚未实现 |
| Inventory(库存) | ❌ mock-only | 后端尚未实现 |
| Samples / Results | ❌ 占位 | 仅占位页 |

---

## 1. Auth（`src/services/auth.ts`）

| 方法 | 路径 | body | response.data | 说明 |
|---|---|---|---|---|
| POST | /auth/login | `{username,password}` | `{access_token,refresh_token,token_type,user,must_change_password}` | 失败 401 |
| POST | /auth/refresh | `{refresh_token}` | `{access_token,refresh_token,token_type}` | |
| POST | /auth/logout | `{refresh_token}` | `{logged_out:true}` | 即时撤销 |
| POST | /auth/change-password | `{old_password,new_password}` | `{must_change_password:false}` | T1.0 仅占位提示 |
| GET | /users/me | — | `User` | |
| GET | /users | — | `User[]` | **后端缺列表端点**，mock 提供；选人/姓名解析依赖 |

`Role = admin | director | project_manager | operator`，中文分别显示为系统管理员、主管、项目负责人、操作员；演示账号仅使用 `project_manager`，历史角色值 `pm` 仍归一为 `project_manager`。

## 2. Projects（`src/services/project.ts`）

| 方法 | 路径 | query/body | response |
|---|---|---|---|
| GET | /projects | `{page,page_size,project_code,name,project_type,status,lead_user_id}` | `PageResult<Project>` |
| POST | /projects | `ProjectInput`(含 `member_ids`) | `Project` |
| GET | /projects/{id} | — | `Project` |
| PATCH | /projects/{id} | `Partial<ProjectInput>` | `Project` |
| DELETE | /projects/{id} | — | `{deleted:true}`（软删） |
| GET | /projects/{id}/members | — | `ProjectMember[]`（含 `user`） |
| POST | /projects/{id}/members | `{user_id,role_in_project}` | `ProjectMember` |
| DELETE | /projects/{id}/members/{user_id} | — | `{deleted:true}` |
| GET | /projects/my-memberships | — | `{managed:Id[],member:Id[]}`（mock 派生） |

`project_status = active|paused|completed|cancelled`；`role_in_project = manager|member`。
**规则**：负责人(lead)∈{admin,director,project_manager}；operator 仅成员；project_manager 新建锁定本人为负责人。

## 3. Experiments（`src/services/experiment.ts`，mock-only）

| 方法 | 路径 | query/body | response |
|---|---|---|---|
| GET | /experiments | `{page,page_size,experiment_no,title,project_id,status,lead_user_id,plan_date_from,plan_date_to}` | `PageResult<Experiment>` |
| POST | /experiments | `ExperimentInput`(含 `material_usages`) | `Experiment` |
| GET | /experiments/{id} | — | `Experiment` |
| PATCH | /experiments/{id} | `Partial<ExperimentInput>` | `Experiment` |
| DELETE | /experiments/{id} | — | `{deleted:true}` |
| GET | /experiments/{id}/activities | — | `ExperimentActivity[]` |
| GET | /experiments/{id}/material-usages | — | `ExperimentMaterialUsage[]` |
| POST | /experiment-records/{id}/dispense | — | `Experiment`（扣库存+写实验来源流水） |

`experiment_status = draft|in_progress|submitted|reviewed|archived`。
物料使用：`usage_role = starting_material|reagent|solvent|catalyst|standard|consumable`；
`stock_status = sufficient|insufficient|no_stock_link`；`outbound_status = pending|dispensed|insufficient|revoked`。
**规则**：保存不扣库存；出库只扣 pending 行且不重复；实际>库存→库存置 0 + `shortage_qty`。

## 4. DailyReports（`src/services/dailyReport.ts`）

| 方法 | 路径 | query/body | response |
|---|---|---|---|
| GET | /daily-reports | `{page,page_size,date_from,date_to,user_id,project_id,related_experiment_id,status,keyword}` | `PageResult<DailyReport>` |
| POST | /daily-reports | `DailyReportInput` | `DailyReport`（status=draft） |
| GET | /daily-reports/{id} | — | `DailyReport` |
| PATCH | /daily-reports/{id} | `Partial<DailyReportInput>` | `DailyReport` |
| POST | /daily-reports/{id}/submit | — | `DailyReport` |
| POST | /daily-reports/{id}/confirm | `{review_comment?}` | `DailyReport` |
| POST | /daily-reports/{id}/return | `{review_comment}`(必填) | `DailyReport` |
| GET | /daily-reports/{id}/activities | — | `DailyReportActivity[]` |
| GET | /daily-reports/{id}/attachments | — | `Attachment[]`（entity_type=`daily_report`） |

`daily_report_status = draft|submitted|returned|confirmed`。日报使用 `items[]` 多条明细；
每条包含工作内容、问题/风险、明日计划和可选关联实验。**不做删除/归档**。
**规则**：提交人=当前用户；作者≠确认人；退回必填原因。

## 5. Inventory（`src/services/inventory.ts`，mock-only）

| 方法 | 路径 | query/body | response |
|---|---|---|---|
| GET | /inventory/materials | — | `Material[]` |
| GET | /inventory/batches | — | `InventoryBatch[]` |
| GET | /inventory | `InventoryListQuery` | `PageResult<InventoryRow>` |
| GET | /inventory/{batchId} | — | `{batch,material}` |
| GET | /inventory/{batchId}/transactions | — | `InventoryTransaction[]` |
| GET | /inventory/{batchId}/experiments | — | 关联实验行（含项目名） |
| POST | /inventory/batches | `NewBatchInput` | `InventoryBatch`（+inbound 流水） |
| POST | /inventory/inbound | `{batch_id,qty,reason?}` | `InventoryBatch` |
| POST | /inventory/adjust | `{batch_id,qty_delta,reason}` | `InventoryBatch` |
| POST | /inventory/{batchId}/freeze | `{frozen}` | `InventoryBatch` |

`material_category = starting_material|reagent|solvent|catalyst|standard|consumable|intermediate|product`；
`batch_status = normal|low|depleted|expired|frozen`；
`transaction_type = inbound|outbound|adjustment|return`，`source_type = manual|experiment`。
**规则**：实验出库写 `source_type=experiment, source_id=experiment_id` 的 outbound；低库存阈值系统 T1.1+。
