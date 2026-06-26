import type { Id } from './common'

export type AttachmentEntity =
  | 'experiment'
  | 'daily_report'
  | 'sample'
  | 'test_task'
  | 'test_result'

export interface Attachment {
  id: Id
  entity_type: AttachmentEntity
  entity_id: Id
  project_id: Id
  original_filename: string
  storage_key: string
  content_type: string
  file_size: number
  checksum_sha256: string
  storage_backend: string
  uploaded_by?: Id | null
  uploaded_at: string
  deleted_at?: string | null
}

export interface AttachmentDeleteResult {
  id: Id
  deleted: boolean
}

export interface AttachmentDownload {
  blob: Blob
  filename: string
  contentType?: string
}
