import { describe, expect, it } from 'vitest'

import { unwrap } from './client'
import { resolveApiMode } from './runtime'

describe('resolveApiMode', () => {
  it('defaults to real mode', () => {
    expect(resolveApiMode(undefined)).toBe('real')
  })

  it('uses mock only when explicitly configured', () => {
    expect(resolveApiMode('mock')).toBe('mock')
    expect(resolveApiMode('real')).toBe('real')
    expect(resolveApiMode('unexpected')).toBe('real')
  })
})
describe('unwrap', () => {
  it('returns data from a successful API envelope', () => {
    expect(unwrap({ code: 0, message: 'ok', data: { status: 'ok' } })).toEqual({
      status: 'ok',
    })
  })

  it('throws a normalized API error for non-zero code', () => {
    expect(() => unwrap({ code: 403, message: 'Forbidden', data: null })).toThrow(
      expect.objectContaining({ code: 403, message: 'Forbidden' }),
    )
  })
})
