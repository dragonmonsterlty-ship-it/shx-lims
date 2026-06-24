import type { AuditFields, Id } from './common'

// 实验记录（T0.8）：项目下的执行记录，区别于项目本身。
// 实验负责人(lead) 可为 project_manager 或 operator；实验参与人(participants) 为项目成员。

export type ExperimentStatus =
  | 'draft'
  | 'planned'
  | 'in_progress'
  | 'submitted'
  | 'reviewed'
  | 'archived'
  | 'completed'
  | 'cancelled'

export interface Experiment extends AuditFields {
  id: Id
  project_id: Id
  project_code?: string
  project_name?: string
  experiment_no: string
  title: string
  record_type?: string
  /** 实验负责人（project_manager 或 operator）。 */
  lead_user_id: Id
  /** 实验参与人（项目成员，可含 operator / project_manager）。 */
  participant_ids: Id[]
  status: ExperimentStatus
  plan_start_date?: string | null
  plan_end_date?: string | null
  experiment_date?: string | null
  objective?: string | null
  steps?: string | null
  result_summary?: string | null
  conclusion?: string | null
  next_step?: string | null
  risk_note?: string | null
  material_usages?: ExperimentMaterialUsage[]
  attachments?: import('./attachment').Attachment[]
  attachment_count?: number
  reagent_usage_count?: number
  is_deleted: boolean
}

export interface ExperimentListQuery {
  page?: number
  page_size?: number
  keyword?: string
  experiment_no?: string
  title?: string
  project_id?: Id
  status?: ExperimentStatus
  lead_user_id?: Id
  plan_date_from?: string
  plan_date_to?: string
}

// ---- 物料使用（与 T0.10 库存模块打通）----
export type UsageRole =
  | 'starting_material'
  | 'reagent'
  | 'solvent'
  | 'catalyst'
  | 'standard'
  | 'consumable'

export type UsageStockStatus = 'sufficient' | 'insufficient' | 'no_stock_link'
export type OutboundStatus = 'pending' | 'dispensed' | 'insufficient' | 'revoked'

/** 实验物料使用记录（持久化快照，batch_id 指向库存批次）。 */
export interface ExperimentMaterialUsage {
  id: Id
  experiment_id: Id
  material_id?: Id | null
  material_code: string
  material_name: string
  batch_id?: Id | null
  batch_no?: string | null
  usage_role: UsageRole
  planned_qty?: number | null
  actual_qty?: number | null
  unit?: string | null
  stock_available?: number | null
  stock_status: UsageStockStatus
  outbound_status: OutboundStatus
  shortage_qty?: number | null
  remark?: string | null
}

/** 表单提交的物料行（其余字段由服务端按库存批次推导）。 */
export interface MaterialUsageInput {
  id?: Id
  batch_id?: Id | null
  usage_role: UsageRole
  planned_qty?: number | null
  actual_qty?: number | null
  remark?: string | null
}

export interface ExperimentInput {
  project_id: Id
  experiment_no?: string
  title: string
  lead_user_id: Id
  participant_ids?: Id[]
  status?: ExperimentStatus
  /** 后端 record_type；前端表单暂无该字段，写入时给安全默认值。 */
  record_type?: string
  plan_start_date?: string | null
  plan_end_date?: string | null
  objective?: string | null
  /** 前端为多行文本；若后续为结构化数组，写入时拼为后端 procedure 文本。 */
  steps?: string | string[] | null
  result_summary?: string | null
  material_usages?: MaterialUsageInput[]
}

/** mock 操作日志条目（创建/编辑/状态变更）。 */
export interface ExperimentActivity {
  id: Id
  experiment_id: Id
  action: string
  actor_id?: Id | null
  at: string
}
