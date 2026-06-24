import type { User } from './auth'
import type { AuditFields, Id } from './common'

export type ProjectStatus = 'active' | 'paused' | 'completed' | 'cancelled'
export type ProjectMemberRole = 'manager' | 'member'

export interface Project extends AuditFields {
  id: Id
  project_code: string
  name: string
  project_type?: string | null
  lead_user_id?: Id | null
  status: ProjectStatus
  priority?: string
  description?: string | null
  start_date?: string | null
  end_date?: string | null
  current_stage?: string | null
  progress?: number
  recent_update?: string | null
  risk_summary?: string | null
  next_plan?: string | null
  remark?: string | null
  member_count?: number
  is_deleted: boolean
}

export interface ProjectMember extends AuditFields {
  id: Id
  project_id: Id
  user_id: Id
  role_in_project: ProjectMemberRole
  /** UI 便利字段：mock/后端可带出关联用户。 */
  user?: User | null
}

export interface ProjectListQuery {
  page?: number
  page_size?: number
  keyword?: string
  project_code?: string
  name?: string
  project_type?: string
  status?: ProjectStatus
  lead_user_id?: Id
  priority?: string
}

export interface ProjectInput {
  project_code: string
  name: string
  project_type?: string | null
  lead_user_id?: Id | null
  status?: ProjectStatus
  description?: string | null
  start_date?: string | null
  end_date?: string | null
  /** 项目组员（role_in_project=member）用户 id 列表，通常为 operator。 */
  member_ids?: Id[]
}
