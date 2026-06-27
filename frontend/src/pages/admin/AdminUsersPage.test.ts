import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

describe('AdminUsersPage contract', () => {
  it('uses admin services and requires confirmation for dangerous operations', () => {
    const source = readFileSync(
      fileURLToPath(new URL('./AdminUsersPage.tsx', import.meta.url)),
      'utf8',
    )

    expect(source).toContain('listAdminUsers')
    expect(source).toContain('updateUserStatus')
    expect(source).toContain('updateUserRole')
    expect(source).toContain('resetUserPassword')
    expect(source).toContain('<Popconfirm')
    expect(source).toContain('modal.confirm')
  })

  it('maps reset-password field errors and falls back to a general message', () => {
    const source = readFileSync(
      fileURLToPath(new URL('./AdminUsersPage.tsx', import.meta.url)),
      'utf8',
    )

    expect(source).toContain("fieldErrors?.new_password")
    expect(source).toContain("message.error")
    expect(source).toContain("min: 8")
  })
})
