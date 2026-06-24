import { unwrap } from '../api/client'
import { mockServer } from '../api/mock'
import type { Attachment, AttachmentEntity, Id } from '../types'

export async function listAttachments(
  entityType: AttachmentEntity,
  entityId: Id,
): Promise<Attachment[]> {
  return unwrap(await mockServer.attachments.listByEntity(entityType, entityId))
}

export async function uploadAttachment(
  entityType: AttachmentEntity,
  entityId: Id,
  file: File,
  actorId: Id,
): Promise<Attachment> {
  return unwrap(
    await mockServer.attachments.upload(
      entityType,
      entityId,
      { name: file.name, size: file.size, type: file.type },
      actorId,
    ),
  )
}

/**
 * 删除附件。真实后端当前无 DELETE 端点；mock 支持。
 * 切真实 API 后若返回 404/405，应提示“当前后端暂不支持附件删除”。
 */
export async function deleteAttachment(id: Id): Promise<void> {
  unwrap(await mockServer.attachments.remove(id))
}

export const attachmentService = { listAttachments, uploadAttachment, deleteAttachment }
