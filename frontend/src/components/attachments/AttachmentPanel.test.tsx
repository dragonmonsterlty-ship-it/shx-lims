import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'

import { AttachmentPanel, clientFileValidationMessage } from './AttachmentPanel'

vi.mock('../../services/attachment', () => ({
  listAttachments: vi.fn(async () => []),
  uploadAttachment: vi.fn(),
  downloadAttachmentToFile: vi.fn(),
  deleteAttachment: vi.fn(),
}))

function renderPanel(canUpload: boolean): string {
  const client = new QueryClient()
  return renderToStaticMarkup(
    <QueryClientProvider client={client}>
      <AttachmentPanel
        entityType="sample"
        entityId={12}
        canUpload={canUpload}
        canDelete={() => false}
      />
    </QueryClientProvider>,
  )
}

describe('AttachmentPanel', () => {
  it('shows file limit hints and upload entry only when allowed', () => {
    const allowed = renderPanel(true)
    const readonly = renderPanel(false)

    expect(allowed).toContain('上传附件')
    expect(allowed).toContain('单个文件不超过 20 MB')
    expect(allowed).toContain('exe')
    expect(readonly).not.toContain('上传附件')
  })

  it('validates dangerous and oversized files before upload', () => {
    expect(
      clientFileValidationMessage(new File(['x'], 'script.exe', { type: 'application/octet-stream' })),
    ).toContain('不允许')

    const largeFile = new File([new Uint8Array(20 * 1024 * 1024 + 1)], 'large.pdf', {
      type: 'application/pdf',
    })
    expect(clientFileValidationMessage(largeFile)).toContain('20 MB')

    expect(
      clientFileValidationMessage(new File(['hello'], 'report.txt', { type: 'text/plain' })),
    ).toBeNull()
  })
})
