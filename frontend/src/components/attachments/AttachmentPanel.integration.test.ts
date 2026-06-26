import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

function read(relativePath: string): string {
  return readFileSync(fileURLToPath(new URL(relativePath, import.meta.url)), 'utf8')
}

describe('T1.6A attachment page integrations', () => {
  it('mounts the unified panel for all five public entity types', () => {
    const experiment = read('../../pages/experiments/ExperimentDetailPage.tsx')
    const report = read('../../pages/dailyReports/DailyReportDetailPage.tsx')
    const sample = read('../../pages/samples/SampleDetailPage.tsx')
    const all = `${experiment}\n${report}\n${sample}`

    expect(experiment).toContain('entityType="experiment"')
    expect(report).toContain('entityType="daily_report"')
    expect(sample).toContain('entityType="sample"')
    expect(sample).toContain('entityType="test_task"')
    expect(sample).toContain('entityType="test_result"')
    expect(all).not.toContain('mock 附件')
    expect(all).not.toContain('暂不支持下载')
  })
})
