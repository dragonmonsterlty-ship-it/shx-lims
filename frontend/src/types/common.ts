// 通用数据契约。字段命名与后端 DATA_MODEL 保持 snake_case 一致，
// 以便未来 mock → 真实 API 切换时无需字段重映射。

export type Id = number

/** 统一响应信封：后端 {code,message,data}，code===0 为成功。 */
export interface ApiEnvelope<T> {
  code: number
  message: string
  data: T
}

/** 统一分页结构。 */
export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

/** 列表查询基础参数。各资源可扩展。 */
export interface PageQuery {
  page?: number
  page_size?: number
  keyword?: string
}

/** 每张业务表的审计字段（软删除表含 is_deleted）。 */
export interface AuditFields {
  created_by?: Id | null
  created_at?: string
  updated_by?: Id | null
  updated_at?: string | null
}
