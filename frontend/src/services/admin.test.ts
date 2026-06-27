import { beforeEach, describe, expect, it, vi } from 'vitest'

import { request } from '../api/http'
import {
  listAdminUsers,
  resetUserPassword,
  updateUserRole,
  updateUserStatus,
} from './admin'

vi.mock('../api/http', () => ({ request: vi.fn() }))

const mockedRequest = vi.mocked(request)

describe('admin service T1.6B contract', () => {
  beforeEach(() => mockedRequest.mockReset())

  it('lists all admin users without unsupported query parameters', async () => {
    mockedRequest.mockResolvedValueOnce([])

    await listAdminUsers()

    expect(mockedRequest).toHaveBeenCalledWith({
      method: 'GET',
      url: '/admin/users',
    })
  })

  it('updates user status through the status endpoint', async () => {
    mockedRequest.mockResolvedValueOnce({})

    await updateUserStatus(5, false)

    expect(mockedRequest).toHaveBeenCalledWith({
      method: 'PATCH',
      url: '/admin/users/5/status',
      data: { is_active: false },
    })
  })

  it('updates user role through the role endpoint', async () => {
    mockedRequest.mockResolvedValueOnce({})

    await updateUserRole(5, 'researcher')

    expect(mockedRequest).toHaveBeenCalledWith({
      method: 'PATCH',
      url: '/admin/users/5/role',
      data: { role: 'researcher' },
    })
  })

  it('resets user password through the reset-password endpoint', async () => {
    mockedRequest.mockResolvedValueOnce({ id: 5, must_change_password: true })

    await resetUserPassword(5, 'newpass123')

    expect(mockedRequest).toHaveBeenCalledWith({
      method: 'POST',
      url: '/admin/users/5/reset-password',
      data: { new_password: 'newpass123' },
    })
  })
})
