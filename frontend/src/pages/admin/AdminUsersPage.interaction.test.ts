// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createElement } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  createAdminUser: vi.fn(),
  listAdminUsers: vi.fn(),
  reload: vi.fn(),
  success: vi.fn(),
  error: vi.fn(),
  confirm: vi.fn(),
}))

vi.mock('../../services/admin', () => ({
  createAdminUser: mocks.createAdminUser,
  listAdminUsers: mocks.listAdminUsers,
  resetUserPassword: vi.fn(),
  updateUserRole: vi.fn(),
  updateUserStatus: vi.fn(),
}))

vi.mock('@ant-design/pro-components', async () => {
  const React = await import('react')
  return {
    PageContainer: ({ children }: { children: React.ReactNode }) =>
      React.createElement('main', null, children),
    ProTable: ({
      actionRef,
      toolBarRender,
    }: {
      actionRef: React.MutableRefObject<{ reload: () => void } | null>
      toolBarRender?: () => React.ReactNode[]
    }) => {
      actionRef.current = { reload: mocks.reload }
      return React.createElement('section', null, toolBarRender?.())
    },
  }
})

vi.mock('antd', async (importOriginal) => {
  const actual = await importOriginal<typeof import('antd')>()
  return {
    ...actual,
    App: {
      ...actual.App,
      useApp: () => ({
        message: { success: mocks.success, error: mocks.error },
        modal: { confirm: mocks.confirm },
      }),
    },
  }
})

import AdminUsersPage from './AdminUsersPage'

async function openCreateModal(user: ReturnType<typeof userEvent.setup>) {
  render(createElement(AdminUsersPage))
  await user.click(screen.getByRole('button', { name: '添加账号' }))
}

async function fillRequiredAccountFields(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText('用户名'), 'new_operator')
  await user.type(screen.getByLabelText('显示名'), 'New Operator')
  await user.type(screen.getByLabelText('初始密码'), 'initial-pass-123')
  fireEvent.mouseDown(screen.getByLabelText('角色'))
  await user.click(await screen.findByText('操作员'))
}

describe('AdminUsersPage create-account flow', () => {
  afterEach(() => cleanup())

  beforeEach(() => {
    vi.clearAllMocks()
    mocks.createAdminUser.mockResolvedValue({})
    mocks.listAdminUsers.mockResolvedValue([])
    window.matchMedia = vi.fn().mockReturnValue({
      matches: false,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })
    const getComputedStyle = window.getComputedStyle.bind(window)
    window.getComputedStyle = (element) => getComputedStyle(element)
  })

  it('opens the modal and submits a validated account', async () => {
    const user = userEvent.setup()
    await openCreateModal(user)
    expect(screen.getByRole('dialog', { name: '添加账号' })).toBeTruthy()

    await fillRequiredAccountFields(user)
    await user.type(screen.getByLabelText('邮箱'), 'new.operator@example.com')
    await user.click(screen.getByRole('button', { name: '创建账号' }))

    await waitFor(() => {
      expect(mocks.createAdminUser).toHaveBeenCalledWith({
        username: 'new_operator',
        display_name: 'New Operator',
        email: 'new.operator@example.com',
        password: 'initial-pass-123',
        role: 'operator',
        is_active: true,
      })
    })
    expect(mocks.success).toHaveBeenCalledWith('账号创建成功')
    expect(mocks.reload).toHaveBeenCalled()
    expect(screen.getByRole('dialog', { name: '添加账号' }).className).toContain('ant-zoom-leave')
  })

  it('blocks empty fields, short passwords, invalid emails, and missing roles', async () => {
    const user = userEvent.setup()
    await openCreateModal(user)

    await user.click(screen.getByRole('button', { name: '创建账号' }))
    expect(await screen.findByText('请输入用户名')).toBeTruthy()
    expect(screen.getByText('请输入初始密码')).toBeTruthy()
    expect(screen.getAllByText('请选择角色').length).toBeGreaterThan(1)

    await user.type(screen.getByLabelText('用户名'), 'new_operator')
    await user.type(screen.getByLabelText('显示名'), 'New Operator')
    await user.type(screen.getByLabelText('邮箱'), 'not-an-email')
    await user.type(screen.getByLabelText('初始密码'), 'short')
    await user.click(screen.getByRole('button', { name: '创建账号' }))

    expect(await screen.findByText('请输入有效的邮箱地址')).toBeTruthy()
    expect(screen.getByText('初始密码至少 8 位')).toBeTruthy()
    expect(mocks.createAdminUser).not.toHaveBeenCalled()
  })

  it('shows a field error when the username already exists', async () => {
    mocks.createAdminUser.mockRejectedValueOnce({
      code: 409,
      status: 409,
      message: 'Username already exists',
    })
    const user = userEvent.setup()
    await openCreateModal(user)
    await fillRequiredAccountFields(user)

    await user.click(screen.getByRole('button', { name: '创建账号' }))

    expect(await screen.findByText('用户名已存在')).toBeTruthy()
    expect(mocks.error).toHaveBeenCalledWith('用户名已存在')
  })

  it('shows the admin-only message when the API returns 403', async () => {
    mocks.createAdminUser.mockRejectedValueOnce({
      code: 403,
      status: 403,
      message: 'Administrator permission required',
    })
    const user = userEvent.setup()
    await openCreateModal(user)
    await fillRequiredAccountFields(user)

    await user.click(screen.getByRole('button', { name: '创建账号' }))

    await waitFor(() => {
      expect(mocks.error).toHaveBeenCalledWith('权限不足，仅系统管理员可以添加账号')
    })
  })
})
