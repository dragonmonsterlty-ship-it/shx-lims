import { beforeEach, describe, expect, it, vi } from 'vitest'

import { httpClient, request } from '../api/http'
import { downloadReagentImportTemplate, importReagentInventory } from './inventory'

vi.mock('../api/http', () => ({
  request: vi.fn(),
  httpClient: { request: vi.fn() },
}))

const mockedRequest = vi.mocked(request)
const mockedHttpRequest = vi.mocked(httpClient.request)

describe('reagent inventory import service', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    mockedRequest.mockReset()
    mockedHttpRequest.mockReset()
  })

  it('downloads the selected Chinese template format', async () => {
    const click = vi.fn()
    const anchor = { href: '', download: '', click, remove: vi.fn() }
    vi.stubGlobal('document', {
      createElement: vi.fn(() => anchor),
      body: { appendChild: vi.fn() },
    })
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => 'blob:template'),
      revokeObjectURL: vi.fn(),
    })
    mockedHttpRequest.mockResolvedValueOnce({
      data: new Blob(['试剂名称,批号']),
      headers: { 'content-disposition': 'attachment; filename="reagent-import-template.csv"' },
    })

    await downloadReagentImportTemplate('csv')

    expect(mockedHttpRequest).toHaveBeenCalledWith({
      method: 'GET',
      url: '/reagents/import-template',
      params: { format: 'csv' },
      responseType: 'blob',
    })
    expect(anchor.download).toBe('reagent-import-template.csv')
    expect(click).toHaveBeenCalledOnce()
  })

  it.each([true, false])('uploads one file with dry_run=%s', async (dryRun) => {
    const file = new File(['content'], 'reagents.csv', { type: 'text/csv' })
    mockedRequest.mockResolvedValueOnce({
      dry_run: dryRun,
      total_rows: 1,
      valid_rows: 1,
      error_rows: 0,
      created_reagents: 1,
      matched_reagents: 0,
      created_lots: 1,
      errors: [],
      warnings: [],
    })

    await importReagentInventory(file, dryRun)

    const config = mockedRequest.mock.calls[0][0]
    expect(config.method).toBe('POST')
    expect(config.url).toBe('/reagents/import')
    expect(config.params).toEqual({ dry_run: dryRun })
    expect(config.data).toBeInstanceOf(FormData)
    expect((config.data as FormData).get('file')).toBe(file)
  })
})
