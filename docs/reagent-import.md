# 试剂库存导入

## 接口

- `GET /api/reagents/import-template?format=csv`：下载 UTF-8 BOM CSV 中文模板。
- `GET /api/reagents/import-template?format=xlsx`：下载 XLSX 中文模板。
- `POST /api/reagents/import?dry_run=true`：校验文件并预览结果，不写数据库。
- `POST /api/reagents/import?dry_run=false`：完整校验通过后正式导入。

上传请求使用 `multipart/form-data`，文件字段名为 `file`。接口要求登录，只有现有试剂主数据管理角色
`admin` 和 `director` 可以下载模板和导入；未登录返回 401，无权限返回 403。

## 文件要求

仅支持 `.csv` 和 `.xlsx`，不支持 `.xls`、`.xlsm` 或其他格式。文件最大 2MB，非空数据行最多
1000 行；全空行会自动跳过。CSV 必须使用 UTF-8 编码（下载的模板自带 BOM），XLSX 使用
OpenPyXL 解析。

模板第一行为以下中文表头，系统会清理表头两侧空格和 UTF-8 BOM：

| 中文表头 | 导入字段 | 现有模型落库字段 |
| --- | --- | --- |
| 试剂名称 | `reagent_name` | `Reagent.name` |
| 批号 | `lot_no` | `ReagentLot.lot_no` |
| 库存数量 | `quantity` | `ReagentLot.quantity` |
| 单位 | `unit` | `ReagentLot.unit`、新试剂的 `Reagent.default_unit` |
| 试剂编码 | `reagent_code` | 无对应字段，返回 warning |
| CAS号 | `cas_no` | `Reagent.cas_no` |
| 供应商 | `supplier` | `Reagent.manufacturer` |
| 货号 | `catalog_no` | `Reagent.catalog_no` |
| 规格 | `specification` | `Reagent.grade` |
| 存放位置 | `location` | `ReagentLot.location` |
| 储存条件 | `storage_condition` | `ReagentLot.storage_condition` |
| 入库日期 | `received_date` | 无对应字段，校验后返回 warning |
| 有效期至 | `expiry_date` | `ReagentLot.expiry_date` |
| 负责人 | `owner` | 无对应字段，返回 warning |
| 备注 | `remark` | 无对应字段，返回 warning |

必填字段为：试剂名称、批号、库存数量、单位。库存数量必须是大于等于 0 的数字。入库日期和
有效期至如填写，使用 `YYYY-MM-DD` 格式。

## 匹配、创建与重复检查

现有核心模型没有试剂编码字段，因此填写试剂编码时系统会返回 warning，不能按该编码可靠匹配
或保存；随后按“试剂名称 + CAS号”匹配。CAS号为空时按试剂名称尝试匹配并返回 warning。
仍无法匹配时创建试剂主数据。

每条有效数据创建一个库存批次。正库存数量还会创建一条 `source_type=import` 的入库流水，
使库存余额和现有库存流水保持一致。同一试剂下数据库已存在相同批号，或上传文件内出现重复的
“试剂 + 批号”时，该行报错，不覆盖已有数据。

## dry-run 与正式导入

建议先调用 `dry_run=true`。响应包含总行数、有效行数、错误行数、预计创建/匹配试剂数量、
预计创建批次数，以及逐行 `errors` 和 `warnings`。

正式导入会先完整解析和校验所有行：

- 有任一 error：不创建试剂、批次或库存流水。
- 无 error：试剂、批次和库存流水在一个数据库事务中写入。
- 写入阶段发生数据库错误：整批回滚并返回通用错误，不暴露服务器路径或堆栈。

常见错误包括必填字段为空、库存数量不是数字或小于 0、日期格式错误、数据库已有重复批号、
文件内部重复批号、表头不完整、文件类型不支持、文件超过 2MB 或超过 1000 行。
