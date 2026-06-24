# 权限矩阵（PERMISSION_MATRIX）

> 四级角色：`admin` / `director` / `project_manager`(pm) / `operator`(op)。
> 前端仅做菜单/按钮显隐与可见性判断（`src/auth/permissions.ts`）；**范围权限以后端行级过滤为唯一真相**。
> 「本项目」= pm 作为负责人(manager)的项目；「参与项目」= 作为成员(member 或 manager)的项目。

图例：✅ 全部 · ✅本 仅本人/本项目 · 👁 只读 · ❌ 不可

## 项目（Project）

| 操作 | admin | director | project_manager | operator |
|---|---|---|---|---|
| 查看项目 | ✅ | ✅ | ✅本(负责/参与) | ✅本(参与) |
| 新建项目 | ✅ | ✅ | ✅(负责人锁定本人) | ❌ |
| 编辑项目 | ✅ | ✅ | ✅本(负责) | ❌ |
| 选择/修改负责人 | ✅(admin/director/pm) | ✅ | ❌(锁定本人) | ❌ |
| 软删除项目 | ✅ | ✅ | ❌ | ❌ |

## 项目成员（ProjectMember）

| 操作 | admin | director | project_manager | operator |
|---|---|---|---|---|
| 查看成员 | ✅ | ✅ | ✅本 | 👁本(参与) |
| 添加/移除组员(operator) | ✅ | ✅ | ✅本(负责) | ❌ |
| 作为负责人 | ✅ | ✅ | ✅ | ❌ |
| 作为组员 | — | — | ✅ | ✅ |

## 实验记录（Experiment）

| 操作 | admin | director | project_manager | operator |
|---|---|---|---|---|
| 查看 | ✅ | ✅ | ✅本(负责/参与项目) | ✅本(参与项目且本人为负责人/参与人) |
| 新建 | ✅ | ✅ | ✅本(负责/参与项目) | ✅本(参与项目，负责人默认本人) |
| 编辑 | ✅ | ✅ | ✅本(负责项目 或 本人为负责人/参与人) | ✅本(本人创建/负责) |
| 删除 | ✅ | ✅ | ❌ | ❌ |
| 负责人/参与人选择 | 所属项目人员 | 所属项目人员 | 所属项目人员 | 所属项目人员(禁跨项目) |

## 实验物料使用（ExperimentMaterialUsage）

| 操作 | admin | director | project_manager | operator |
|---|---|---|---|---|
| 填写/编辑物料行 | ✅ | ✅ | ✅(可编辑的实验) | ✅本(本人创建/负责的实验) |
| 查看物料使用 | ✅ | ✅ | ✅本 | ✅本 |

## 实验出库（Dispense）

| 操作 | admin | director | project_manager | operator |
|---|---|---|---|---|
| 确认出库 | ✅ | ✅ | ✅本(仅自己**负责项目**下实验) | ❌ |

## 工作日报（DailyReport）

| 操作 | admin | director | project_manager | operator |
|---|---|---|---|---|
| 查看 | ✅ | ✅ | ✅本(本人 + 负责项目成员) | ✅本(仅本人) |
| 新建本人日报 | ✅ | ✅ | ✅ | ✅ |
| 编辑/提交(草稿/退回) | ✅本 | ✅本 | ✅本 | ✅本 |
| 确认/退回 | ✅(全部) | ✅(全部) | ✅本(负责项目下他人已提交) | ❌ |
| 删除 | ❌ | ❌ | ❌ | ❌ |

> 提交人锁定当前用户；作者≠确认人；退回必填原因。

## 库存（Inventory）查看

| 操作 | admin | director | project_manager | operator |
|---|---|---|---|---|
| 查看库存/批次/流水/关联实验 | ✅ | ✅ | ✅ | ✅ |

## 库存调整（入库/调整/冻结/新增批次）

| 操作 | admin | director | project_manager | operator |
|---|---|---|---|---|
| 新增物料/批次 | ✅ | ✅ | ❌(占位) | ❌ |
| 手动入库 | ✅ | ✅ | ❌ | ❌ |
| 手动调整 | ✅ | ✅ | ❌ | ❌ |
| 冻结/解冻 | ✅ | ✅ | ❌ | ❌ |

## 系统管理 / 菜单

| 项 | admin | director | project_manager | operator |
|---|---|---|---|---|
| 系统管理菜单(/admin) | ✅ | ❌ | ❌ | ❌ |
| 其它业务菜单 | ✅ | ✅ | ✅ | ✅ |
