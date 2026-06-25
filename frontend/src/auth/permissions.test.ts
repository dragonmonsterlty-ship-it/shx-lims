import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

import { roleLabel } from './permissions'
import { normalizeRole } from '../api/adapters'

describe('role terminology', () => {
  it('labels director as 主管 and keeps it as the director role', () => {
    expect(roleLabel.director).toBe('主管')
    expect(normalizeRole('director')).toBe('director')
  })

  it('labels project_manager as 项目负责人 and keeps pm as its alias', () => {
    expect(roleLabel.project_manager).toBe('项目负责人')
    expect(normalizeRole('project_manager')).toBe('project_manager')
    expect(normalizeRole('pm')).toBe('project_manager')
  })

  it('offers only the project_manager demo account for 项目负责人', () => {
    const loginPage = readFileSync(
      fileURLToPath(new URL('../pages/auth/LoginPage.tsx', import.meta.url)),
      'utf8',
    )

    expect(loginPage).not.toContain("{ u: 'pm'")
    expect(loginPage.match(/\{ u: 'project_manager', label: '项目负责人' \}/g)).toHaveLength(2)
  })
})
