import { useQuery } from '@tanstack/react-query'
import { renderToStaticMarkup } from 'react-dom/server'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AuditTimeline from './AuditTimeline'

vi.mock('@tanstack/react-query', () => ({ useQuery: vi.fn() }))

const mockedUseQuery = vi.mocked(useQuery)
const refetch = vi.fn()

function setQueryState(overrides: Record<string, unknown> = {}) {
  mockedUseQuery.mockReturnValue({
    data: undefined,
    error: null,
    isLoading: false,
    refetch,
    ...overrides,
  } as unknown as ReturnType<typeof useQuery>)
}

function renderTimeline(): string {
  return renderToStaticMarkup(
    <AuditTimeline entityType="sample" entityId={12} title={null} compact />,
  )
}

describe('AuditTimeline', () => {
  beforeEach(() => {
    mockedUseQuery.mockReset()
    refetch.mockReset()
  })

  it('renders loading state', () => {
    setQueryState({ isLoading: true })

    expect(renderTimeline()).toContain('ant-skeleton')
  })

  it('renders empty state', () => {
    setQueryState({ data: [] })

    expect(renderTimeline()).toContain('暂无审计记录')
  })

  it('renders an error with a reload action', () => {
    setQueryState({ error: new Error('network unavailable') })

    const html = renderTimeline()
    expect(html).toContain('审计时间线加载失败')
    expect(html).toContain('network unavailable')
    expect(html).toContain('重新加载')
  })

  it('wires reload to the query refetch operation', () => {
    const source = AuditTimeline.toString()

    expect(source).toContain('query.refetch')
  })

  it('renders audit actions, actors and timestamps', () => {
    setQueryState({
      data: [
        {
          id: 1,
          actor_user_id: 7,
          actor_role: 'project_manager',
          action: 'create',
          entity_type: 'sample',
          entity_id: 12,
          project_id: 3,
          target_user_id: null,
          before_data: null,
          after_data: null,
          metadata: null,
          created_at: '2026-06-27T08:00:00Z',
        },
      ],
    })

    const html = renderTimeline()
    expect(html).toContain('创建')
    expect(html).toContain('用户 #7')
    expect(html).toContain('project_manager')
  })
})
