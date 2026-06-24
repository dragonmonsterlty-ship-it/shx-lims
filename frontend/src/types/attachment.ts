import type { Id } from './common'

export type AttachmentEntity = 'sample' | 'result' | 'experiment' | 'daily_report'

export interface Attachment {
  id: Id
  entity_type: AttachmentEntity
  entity_id: Id
  file_name: string
  storage_key: string
  file_type?: string | null
  content_type_detected?: string | null
  file_size?: number | null
  sha256?: string | null
  thumbnail_key?: string | null
  upload_status: string
  preview_status?: string | null
  uploaded_by?: Id | null
  uploaded_at: string
}
