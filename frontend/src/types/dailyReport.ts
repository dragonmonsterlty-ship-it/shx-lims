import type { AuditFields, Id } from './common'
import type { User } from './auth'

// 工作日报（T0.9）：组员每日提交，主管/主任/admin 查看、确认、退回。
// 取代早期的 daily_log 占位，复用项目/成员与实验记录关系。

export type DailyReportStatus =
  | 'draft'
  | 'submitted'
  | 'returned'
  | 'confirmed'

export interface DailyReportItem {
  id: Id
  daily_report_id: Id
  project_id?: Id | null
  experiment_record_id?: Id | null
  work_type: string
  content: string
  progress_note?: string | null
  hours_spent?: number | string | null
  problem_note?: string | null
  next_step?: string | null
  sort_order: number
}

export interface DailyReport extends AuditFields {
  id: Id
  /** 提交人。 */
  user_id: Id
  user?: User
  project_id: Id | null
  /** 关联实验记录（可选）。 */
  related_experiment_id?: Id | null
  report_date: string
  work_content: string
  issues_risks?: string | null
  next_plan?: string | null
  status: DailyReportStatus
  submitted_at?: string | null
  /** 确认人。 */
  reviewed_by?: Id | null
  reviewed_at?: string | null
  review_comment?: string | null
  items?: DailyReportItem[]
  attachments?: import('./attachment').Attachment[]
  item_count?: number
  project_count?: number
  experiment_record_count?: number
  is_deleted: boolean
}

export interface DailyReportListQuery {
  page?: number
  page_size?: number
  date_from?: string
  date_to?: string
  user_id?: Id
  project_id?: Id
  related_experiment_id?: Id
  status?: DailyReportStatus
  keyword?: string
}

/** 日报明细写入条目（前端 → 后端 items[]）。 */
export interface DailyReportItemInput {
  project_id?: Id | null
  experiment_record_id?: Id | null
  work_type?: string
  content: string
  progress_note?: string | null
  hours_spent?: number | null
  problem_note?: string | null
  next_step?: string | null
  sort_order?: number
}

export interface DailyReportInput {
  project_id?: Id
  related_experiment_id?: Id | null
  report_date: string
  work_content?: string
  issues_risks?: string | null
  next_plan?: string | null
  /** 多条明细；省略则由扁平字段自动转为单条 item，兼容旧表单。 */
  items?: DailyReportItemInput[]
}

/** mock 操作记录（创建/编辑/提交/确认/退回）。 */
export interface DailyReportActivity {
  id: Id
  report_id: Id
  action: string
  actor_id?: Id | null
  at: string
}
