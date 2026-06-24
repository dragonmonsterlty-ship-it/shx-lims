import type { AuditFields, Id } from './common'

export type SampleStatus =
  | 'registered'
  | 'in_testing'
  | 'pending_review'
  | 'completed'
  | 'cancelled'

export type TestStatus = 'pending' | 'in_progress' | 'done'
export type SamplePriority = 'normal' | 'urgent'

export interface Sample extends AuditFields {
  id: Id
  sample_code: string
  project_id: Id
  compound_name: string
  name: string
  sample_type?: string | null
  batch_no?: string | null
  structure_smiles?: string | null
  source?: string | null
  status: SampleStatus
  priority: SamplePriority
  received_at?: string | null
  due_date?: string | null
  notes?: string | null
  is_deleted: boolean
}

export interface TestMethod {
  id: Id
  code: string
  name: string
  method?: string | null
  unit?: string | null
  spec_lower?: number | null
  spec_upper?: number | null
  spec_text?: string | null
  is_active: boolean
}

export interface SampleTest extends AuditFields {
  id: Id
  sample_id: Id
  test_method_id: Id
  assigned_to?: Id | null
  status: TestStatus
}

export interface SampleListQuery {
  page?: number
  page_size?: number
  keyword?: string
  project_id?: Id
  status?: SampleStatus
  priority?: SamplePriority
}

/** 样品详情「检测项与结果」的扁平行视图（join 后供表格直接消费）。 */
export interface SampleTestRow {
  id: Id
  sample_id: Id
  test_method_id: Id
  method_code: string
  method_name: string
  unit?: string | null
  spec_lower?: number | null
  spec_upper?: number | null
  spec_text?: string | null
  assigned_to?: Id | null
  status: TestStatus
  value_num?: number | null
  value_text?: string | null
  judgment?: import('./result').Judgment | null
  review_status?: import('./result').ReviewStatus | null
  result_id?: Id | null
}
