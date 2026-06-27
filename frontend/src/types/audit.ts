export interface AuditLog {
  id: number
  actor_user_id: number | null
  actor_role: string | null
  action: string
  entity_type: string
  entity_id: number
  project_id: number | null
  target_user_id: number | null
  before_data: unknown
  after_data: unknown
  metadata: unknown
  created_at: string
}

export interface AuditLogListQuery {
  entity_type?: string
  entity_id?: number
  project_id?: number
  actor_user_id?: number
  action?: string
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
}

export interface AuditLogListData {
  items: AuditLog[]
  total: number
  page: number
  page_size: number
}
