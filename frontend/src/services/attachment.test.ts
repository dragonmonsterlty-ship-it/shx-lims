import { beforeEach, describe, expect, it, vi } from 'vitest'

import { httpClient, request } from '../api/http'
import {
  deleteAttachment,
  downloadAttachment,
  downloadAttachmentToFile,
  listAttachments,
  uploadAttachment,
} from './attachment'

vi.mock('../api/http', () => ({
  request: vi.fn(),
  httpClient: {
    request: vi.fn(),
  },
}))

const mockedRequest = vi.mocked(request)
const mockedHttpRequest = vi.mocked(httpClient.request)

describe('attachment service real API contract', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    mockedRequest.mockReset()
    mockedHttpRequest.mockReset()
  })

  it('lists attachments by public entity pair', async () => {
    mockedRequest.mockResolvedValueOnce([])

    await listAttachments('sample', 12)

    expect(mockedRequest).toHaveBeenCalledWith({
      method: 'GET',
      url: '/attachments',
      params: { entity_type: 'sample', entity_id: 12 },
    })
  })

  it('uploads attachments through multipart form data with progress', async () => {
    const onProgress = vi.fn()
    const file = new File(['hello'], 'report.txt', { type: 'text/plain' })
    mockedRequest.mockResolvedValueOnce({ id: 1 })

    await uploadAttachment('test_task', 15, file, onProgress)

    const config = mockedRequest.mock.calls[0][0]
    expect(config.method).toBe('POST')
    expect(config.url).toBe('/attachments')
    expect(config.data).toBeInstanceOf(FormData)
    expect(config.onUploadProgress).toBeTypeOf('function')
    config.onUploadProgress?.({ loaded: 5, total: 10, bytes: 5, lengthComputable: true } as never)
    expect(onProgress).toHaveBeenCalledWith(50)
  })

  it('downloads attachment bytes as a blob and exposes response headers', async () => {
    const blob = new Blob(['hello'], { type: 'text/plain' })
    mockedHttpRequest.mockResolvedValueOnce({
      data: blob,
      headers: { 'content-disposition': "attachment; filename*=UTF-8''report.txt" },
    })

    const response = await downloadAttachment(8)

    expect(mockedHttpRequest).toHaveBeenCalledWith({
      method: 'GET',
      url: '/attachments/8/download',
      responseType: 'blob',
    })
    expect(response.blob).toBe(blob)
    expect(response.filename).toBe('report.txt')
  })

  it('deletes attachments through the unified endpoint', async () => {
    mockedRequest.mockResolvedValueOnce({ id: 8, deleted: true })

    await deleteAttachment(8)

    expect(mockedRequest).toHaveBeenCalledWith({
      method: 'DELETE',
      url: '/attachments/8',
    })
  })

  it('saves a downloaded blob using the response filename and revokes object URL', async () => {
    const click = vi.fn()
    const anchor = {
      href: '',
      download: '',
      click,
      remove: vi.fn(),
    }
    const appendChild = vi.fn((node) => node)
    vi.stubGlobal('document', {
      createElement: vi.fn(() => anchor),
      body: { appendChild },
    })
    const createObjectURL = vi.fn(() => 'blob:attachment')
    const revokeObjectURL = vi.fn()
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL })
    mockedHttpRequest.mockResolvedValueOnce({
      data: new Blob(['hello'], { type: 'text/plain' }),
      headers: { 'content-disposition': 'attachment; filename="plain.txt"' },
    })

    await downloadAttachmentToFile(9)

    expect(anchor.href).toBe('blob:attachment')
    expect(anchor.download).toBe('plain.txt')
    expect(click).toHaveBeenCalled()
    expect(createObjectURL).toHaveBeenCalled()
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:attachment')
  })
})
