import type { AuditFields, Id } from './common'

export type Judgment = 'pass' | 'fail' | 'oos'
export type ReviewStatus = 'pending' | 'approved' | 'rejected'

export interface Result extends AuditFields {
  id: Id
  sample_test_id: Id
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
  review_status?: ReviewStatus
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
  entered_by?: Id | null
  entered_at?: string | null
}
