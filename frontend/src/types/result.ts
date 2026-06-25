import type { AuditFields, Id } from './common'

export type Judgment = 'pass' | 'fail' | 'oos'
export type ResultStatus = 'draft' | 'submitted' | 'approved' | 'rejected'
export type ReviewStatus = ResultStatus | 'pending'

export interface Result extends AuditFields {
  id: Id
  task_id: Id
  sample_test_id: Id
  result_data: unknown
  conclusion?: string | null
  status: ResultStatus
  submitted_by?: Id | null
  submitted_at?: string | null
  value_num?: number | null
  value_text?: string | null
  judgment?: Judgment | null
  entered_by?: Id | null
  entered_at?: string | null
  review_status: ReviewStatus
  reviewed_by?: Id | null
  reviewed_at?: string | null
  review_comment?: string | null
}

export interface ResultReviewQuery {
  page?: number
  page_size?: number
  keyword?: string
  project_id?: Id
  review_status?: ResultStatus
}

/** 审核工作台的扁平行视图（join 样品/方法/结果）。 */
export interface ResultRow {
  id: Id
  sample_test_id: Id
  sample_id: Id
  sample_code: string
  project_id: Id
  method_name: string
  unit?: string | null
  value_num?: number | null
  value_text?: string | null
  judgment?: Judgment | null
  review_status: ReviewStatus
  status: ResultStatus
  result_data: unknown
  conclusion?: string | null
  submitted_by?: Id | null
  submitted_at?: string | null
  entered_by?: Id | null
  entered_at?: string | null
}

export interface ResultDraftInput {
  result_data: unknown
  conclusion?: string | null
}
