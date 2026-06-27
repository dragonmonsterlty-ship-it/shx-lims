import { beforeEach, describe, expect, it, vi } from 'vitest'

import { request } from '../api/http'
import { getEntityAuditTimeline, listAuditLogs } from './audit'

vi.mock('../api/http', () => ({ request: vi.fn() }))

const mockedRequest = vi.mocked(request)

describe('audit service T1.6B contract', () => {
  beforeEach(() => mockedRequest.mockReset())

  it('lists audit logs with only defined query parameters', async () => {
    mockedRequest.mockResolvedValueOnce({ items: [], total: 0, page: 2, page_size: 25 })

    await listAuditLogs({
      entity_type: 'sample',
      project_id: 12,
      action: undefined,
      date_from: '2026-06-01T00:00:00Z',
      page: 2,
      page_size: 25,
    })

    expect(mockedRequest).toHaveBeenCalledWith({
      method: 'GET',
      url: '/audit-logs',
      params: {
        entity_type: 'sample',
        project_id: 12,
        date_from: '2026-06-01T00:00:00Z',
        page: 2,
        page_size: 25,
      },
    })
  })

  it('gets an entity audit timeline through the encoded entity path', async () => {
    mockedRequest.mockResolvedValueOnce([])

    await getEntityAuditTimeline('daily report', 9)

    expect(mockedRequest).toHaveBeenCalledWith({
      method: 'GET',
      url: '/audit-logs/entity/daily%20report/9',
    })
  })
})
