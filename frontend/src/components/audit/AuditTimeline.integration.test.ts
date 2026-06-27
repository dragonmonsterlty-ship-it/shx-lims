import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

function read(relativePath: string): string {
  return readFileSync(fileURLToPath(new URL(relativePath, import.meta.url)), 'utf8')
}

describe('T1.8 entity detail audit timeline integrations', () => {
  it('passes the loaded experiment id to the experiment timeline', () => {
    const source = read('../../pages/experiments/ExperimentDetailPage.tsx')

    expect(source).toContain('import { AuditTimeline }')
    expect(source).toContain('entityType="experiment" entityId={exp.id}')
  })

  it('passes the loaded daily report id to the daily report timeline', () => {
    const source = read('../../pages/dailyReports/DailyReportDetailPage.tsx')

    expect(source).toContain('import { AuditTimeline }')
    expect(source).toContain('entityType="daily_report" entityId={report.id}')
  })

  it('passes the loaded sample id to the sample timeline', () => {
    const source = read('../../pages/samples/SampleDetailPage.tsx')

    expect(source).toContain('import { AuditTimeline }')
    expect(source).toContain('entityType="sample" entityId={sample.id}')
  })
})
