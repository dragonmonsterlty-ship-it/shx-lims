import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

import { buildMenu } from '../layouts/menu'

describe('T1.7.2 route and menu access', () => {
  it('shows user management only to admin and audit logs to admin and project manager', () => {
    expect(buildMenu('admin').map((item) => item.path)).toEqual(
      expect.arrayContaining(['/admin/users', '/audit-logs']),
    )
    expect(buildMenu('project_manager').map((item) => item.path)).toContain('/audit-logs')
    expect(buildMenu('project_manager').map((item) => item.path)).not.toContain('/admin/users')

    for (const role of ['director', 'researcher', 'operator', 'viewer'] as const) {
      expect(buildMenu(role).map((item) => item.path)).not.toContain('/admin/users')
      expect(buildMenu(role).map((item) => item.path)).not.toContain('/audit-logs')
    }
  })

  it('guards admin and audit routes with their backend role boundaries', () => {
    const routerSource = readFileSync(
      fileURLToPath(new URL('./index.tsx', import.meta.url)),
      'utf8',
    )

    expect(routerSource).toContain("path: 'admin/users'")
    expect(routerSource).toContain("<RoleGuard allow={['admin']}")
    expect(routerSource).toContain("path: 'audit-logs'")
    expect(routerSource).toContain("<RoleGuard allow={['admin', 'project_manager']}")
    expect(routerSource).toContain('<Navigate to="/admin/users" replace />')
  })
})
