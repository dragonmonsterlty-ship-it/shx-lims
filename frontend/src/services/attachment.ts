import type { AxiosProgressEvent } from 'axios'

import { endpoints } from '../api/endpoints'
import { normalizeApiError } from '../api/errors'
import { httpClient, request } from '../api/http'
import type {
  Attachment,
  AttachmentDeleteResult,
  AttachmentDownload,
  AttachmentEntity,
  Id,
} from '../types'

export async function listAttachments(
  entityType: AttachmentEntity,
  entityId: Id,
): Promise<Attachment[]> {
  return request<Attachment[]>({
    method: 'GET',
    url: endpoints.attachments.root,
    params: { entity_type: entityType, entity_id: entityId },
  })
}

export async function uploadAttachment(
  entityType: AttachmentEntity,
  entityId: Id,
  file: File,
  onProgress?: (percent: number) => void,
): Promise<Attachment> {
  const formData = new FormData()
  formData.append('entity_type', entityType)
  formData.append('entity_id', String(entityId))
  formData.append('file', file)

  return request<Attachment>({
    method: 'POST',
    url: endpoints.attachments.root,
    data: formData,
    onUploadProgress: (event: AxiosProgressEvent) => {
      if (event.total && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100))
      }
    },
  })
}

export async function downloadAttachment(id: Id): Promise<AttachmentDownload> {
  try {
    const response = await httpClient.request<Blob>({
      method: 'GET',
      url: endpoints.attachments.download(id),
      responseType: 'blob',
    })
    return {
      blob: response.data,
      filename: filenameFromContentDisposition(response.headers?.['content-disposition']) ?? `attachment-${id}`,
      contentType: stringHeader(response.headers?.['content-type']),
    }
  } catch (error) {
    throw normalizeApiError(error)
  }
}

export async function downloadAttachmentToFile(id: Id): Promise<void> {
  const { blob, filename } = await downloadAttachment(id)
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  try {
    anchor.click()
  } finally {
    anchor.remove()
    URL.revokeObjectURL(url)
  }
}

export async function deleteAttachment(id: Id): Promise<AttachmentDeleteResult> {
  return request<AttachmentDeleteResult>({
    method: 'DELETE',
    url: endpoints.attachments.detail(id),
  })
}

export function filenameFromContentDisposition(value: unknown): string | undefined {
  if (typeof value !== 'string' || !value) return undefined
  const utf8Match = value.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1].trim())
    } catch {
      return utf8Match[1].trim()
    }
  }
  const quotedMatch = value.match(/filename="([^"]+)"/i)
  if (quotedMatch?.[1]) return quotedMatch[1]
  const bareMatch = value.match(/filename=([^;]+)/i)
  return bareMatch?.[1]?.trim()
}

function stringHeader(value: unknown): string | undefined {
  return typeof value === 'string' ? value : undefined
}

export const attachmentService = {
  listAttachments,
  uploadAttachment,
  downloadAttachment,
  downloadAttachmentToFile,
  deleteAttachment,
}
