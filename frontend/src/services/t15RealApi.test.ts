import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

function read(relativePath: string): string {
  return readFileSync(fileURLToPath(new URL(relativePath, import.meta.url)), 'utf8')
}

describe('T1.5 real API boundary', () => {
  it('does not route sample or result services through the mock server', () => {
    const sampleService = read('./sample.ts')
    const resultService = read('./result.ts')

    expect(sampleService).not.toContain('mockServer')
    expect(sampleService).not.toContain('USE_MOCK')
    expect(resultService).not.toContain('mockServer')
    expect(resultService).not.toContain('USE_MOCK')
  })

  it('does not keep sample, task, method, or result fixtures in the mock database', () => {
    const mockDb = read('../api/mock/db.ts')
    const mockServer = read('../api/mock/server.ts')

    expect(mockDb).not.toMatch(/export const (samples|sampleTests|testMethods|results)\b/)
    expect(mockServer).not.toMatch(/^\s{2}(samples|testMethods|results):\s*\{/m)
  })

  it('keeps the real API smoke on the full reject, edit, resubmit, approve path', () => {
    const smoke = read('../../scripts/verify-real-api.mjs')

    expect(smoke).toContain('/reject')
    expect(smoke).toContain("status !== 'rejected'")
    expect(smoke).toContain("method: 'PATCH'")
    expect(smoke.match(/\/submit/g)?.length ?? 0).toBeGreaterThanOrEqual(2)
    expect(smoke).toContain('/approve')
  })
})
