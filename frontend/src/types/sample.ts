import type { AuditFields, Id } from './common'

export type SampleStatus =
  | 'registered'
  | 'in_testing'
  | 'pending_review'
  | 'completed'
  | 'cancelled'

export type TestStatus = 'pending' | 'in_progress' | 'done'
export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'cancelled'
export type SamplePriority = 'normal' | 'urgent'

export interface Sample extends AuditFields {
  id: Id
  sample_no: string
  sample_code: string
  project_id: Id
  compound_name?: string | null
  name: string
  type?: string | null
  sample_type?: string | null
  batch_no?: string | null
  amount?: number | null
  unit?: string | null
  storage_condition?: string | null
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
  category?: string | null
  version?: string | null
  description?: string | null
  method?: string | null
  unit?: string | null
  spec_lower?: number | null
  spec_upper?: number | null
  spec_text?: string | null
  is_active: boolean
  created_by?: Id | null
  created_at?: string
  updated_by?: Id | null
  updated_at?: string | null
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

export interface SampleInput {
  project_id: Id
  sample_no: string
  name: string
  type?: string | null
  source?: string | null
  batch_no?: string | null
  amount?: number | null
  unit?: string | null
  storage_condition?: string | null
  priority?: SamplePriority
  due_date?: string | null
  notes?: string | null
}

export interface TestTask extends AuditFields {
  id: Id
  sample_id: Id
  method_id: Id
  test_method_id: Id
  assigned_to?: Id | null
  status: TaskStatus
  priority: string
  due_date?: string | null
  sample: {
    id: Id
    project_id: Id
    sample_no: string
    name: string
    status: SampleStatus
  }
  method: {
    id: Id
    code: string
    name: string
    category?: string | null
    version?: string | null
  }
  method_code: string
  method_name: string
  result_id?: Id | null
  result_status?: import('./result').ResultStatus | null
  review_status?: import('./result').ResultStatus | null
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
  status: TestStatus | TaskStatus
  value_num?: number | null
  value_text?: string | null
  judgment?: import('./result').Judgment | null
  review_status?: import('./result').ReviewStatus | null
  result_id?: Id | null
}
