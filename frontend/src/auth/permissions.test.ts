import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

import { canExecuteTestTask, canManageSample, canReviewTestResult, roleLabel } from './permissions'
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

  it('enforces T1.5 manager, analyst and viewer capabilities', () => {
    const admin = { id: 1, role: 'admin' as const }
    const manager = { id: 2, role: 'project_manager' as const }
    const analyst = { id: 3, role: 'operator' as const }
    const viewer = { id: 4, role: 'director' as const }
    const scope = { managed: new Set([10]), member: new Set([10]) }

    expect(canManageSample(admin, 999, scope)).toBe(true)
    expect(canManageSample(manager, 10, scope)).toBe(true)
    expect(canManageSample(analyst, 10, scope)).toBe(false)
    expect(canManageSample(viewer, 10, scope)).toBe(false)
    expect(canExecuteTestTask(analyst, { assigned_to: 3, status: 'pending' })).toBe(true)
    expect(canExecuteTestTask(analyst, { assigned_to: 8, status: 'pending' })).toBe(false)
    expect(canReviewTestResult(manager, 10, 'submitted', scope)).toBe(true)
    expect(canReviewTestResult(viewer, 10, 'submitted', scope)).toBe(false)
  })
})
