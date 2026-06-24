import { describe, expect, it } from 'vitest'

import { getStatusMeta } from './status'

describe('status meta', () => {
  it('shows backend experiment submitted/archived labels (display compatibility)', () => {
    expect(getStatusMeta('experiment', 'submitted').label).toBe('已提交')
    expect(getStatusMeta('experiment', 'archived').label).toBe('已归档')
  })

  it('falls back to the raw value for unknown status without throwing', () => {
    expect(getStatusMeta('experiment', 'weird_status')).toEqual({
      color: 'default',
      label: 'weird_status',
    })
  })
})
