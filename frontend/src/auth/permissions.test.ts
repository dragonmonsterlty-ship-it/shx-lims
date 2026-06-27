import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

import {
  canManageUsers,
  canDeleteAttachment,
  canCreateReport,
  canExecuteTestTask,
  canManageSample,
  canReviewTestResult,
  canUseAdminRoute,
  canUploadAttachment,
  canViewAuditLogs,
  canViewUserAuditTimeline,
  can,
  roleLabel,
} from './permissions'
import { normalizeRole } from '../api/adapters'

describe('role terminology', () => {
  it('parses all six backend roles and safely falls back to viewer', () => {
    expect(
      ['admin', 'director', 'project_manager', 'researcher', 'operator', 'viewer'].map(
        normalizeRole,
      ),
    ).toEqual(['admin', 'director', 'project_manager', 'researcher', 'operator', 'viewer'])
    expect(normalizeRole('unknown-role')).toBe('viewer')
    expect(normalizeRole(undefined)).toBe('viewer')
  })

  it('provides labels for all six backend roles', () => {
    expect(roleLabel).toEqual({
      admin: '系统管理员',
      director: '主管',
      project_manager: '项目负责人',
      researcher: '研究员',
      operator: '操作员',
      viewer: '只读用户',
    })
  })

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

  it('enforces T1.6A attachment upload and delete capabilities', () => {
    const admin = { id: 1, role: 'admin' as const }
    const manager = { id: 2, role: 'project_manager' as const }
    const operator = { id: 3, role: 'operator' as const }
    const director = { id: 4, role: 'director' as const }
    const scope = { managed: new Set([10]), member: new Set([10]) }
    const editableContext = {
      entityType: 'test_task' as const,
      projectId: 10,
      editable: true,
      assignedTo: 3,
    }
    const otherProjectContext = { ...editableContext, projectId: 99 }
    const attachment = { id: 7, uploaded_by: 3 }
    const managerAttachment = { id: 8, uploaded_by: 2 }

    expect(canUploadAttachment(admin, editableContext, scope)).toBe(true)
    expect(canUploadAttachment(manager, editableContext, scope)).toBe(true)
    expect(canUploadAttachment(manager, otherProjectContext, scope)).toBe(false)
    expect(canUploadAttachment(operator, editableContext, scope)).toBe(true)
    expect(canUploadAttachment(director, editableContext, scope)).toBe(false)
    expect(canUploadAttachment(operator, { ...editableContext, editable: false }, scope)).toBe(false)

    expect(canDeleteAttachment(admin, managerAttachment, editableContext, scope)).toBe(true)
    expect(canDeleteAttachment(manager, managerAttachment, editableContext, scope)).toBe(true)
    expect(canDeleteAttachment(operator, attachment, editableContext, scope)).toBe(true)
    expect(canDeleteAttachment(operator, managerAttachment, editableContext, scope)).toBe(false)
    expect(canDeleteAttachment(director, attachment, editableContext, scope)).toBe(false)
  })

  it('enforces T1.6B admin and audit capabilities', () => {
    expect(canManageUsers('admin')).toBe(true)
    expect(canUseAdminRoute('admin')).toBe(true)
    expect(canViewAuditLogs('admin')).toBe(true)
    expect(canViewAuditLogs('project_manager')).toBe(true)

    for (const role of ['director', 'researcher', 'operator', 'viewer'] as const) {
      expect(canManageUsers(role)).toBe(false)
      expect(canUseAdminRoute(role)).toBe(false)
      expect(canViewAuditLogs(role)).toBe(false)
    }

    expect(canManageUsers('project_manager')).toBe(false)
    expect(canUseAdminRoute('project_manager')).toBe(false)
    expect(canViewUserAuditTimeline({ id: 1, role: 'admin' }, 99)).toBe(true)
    expect(canViewUserAuditTimeline({ id: 7, role: 'viewer' }, 7)).toBe(true)
    expect(canViewUserAuditTimeline({ id: 7, role: 'viewer' }, 8)).toBe(false)
  })

  it('keeps the viewer fallback read-only', () => {
    const scope = { managed: new Set([10]), member: new Set([10]) }

    expect(can.writeData('viewer')).toBe(false)
    expect(can.review('viewer')).toBe(false)
    expect(canCreateReport('viewer')).toBe(false)
    expect(
      canUploadAttachment(
        { id: 7, role: 'viewer' },
        { entityType: 'sample', projectId: 10, editable: true, ownerId: 7 },
        scope,
      ),
    ).toBe(false)
  })
})
