import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

import { formatAuditJson, summarizeAuditJson } from './auditView'

describe('AuditLogPage contract', () => {
  it('formats null, primitive and nested JSON without throwing', () => {
    expect(summarizeAuditJson(null)).toBe('—')
    expect(summarizeAuditJson('plain')).toBe('plain')
    expect(summarizeAuditJson({ status: 'draft', nested: { value: 1 } }, 20)).toContain('…')
    expect(formatAuditJson({ nested: [1, true, null] })).toContain('"nested"')
    expect(formatAuditJson(undefined)).toBe('—')
  })

  it('uses backend pagination, filters, empty state and backend error messages', () => {
    const source = readFileSync(
      fileURLToPath(new URL('./AuditLogPage.tsx', import.meta.url)),
      'utf8',
    )

    expect(source).toContain('listAuditLogs')
    expect(source).toContain('page: params.current')
    expect(source).toContain('page_size: params.pageSize')
    expect(source).toContain('date_from')
    expect(source).toContain('date_to')
    expect(source).toContain('<SketchEmpty')
    expect(source).toContain('loadError')
    expect(source).toContain('查看详情')
  })
})
