// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { MemoryRouter, Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import { AuthContext, type AuthContextValue } from '../auth/authContext'
import type { ModuleKey, Role, User } from '../types'
import ModuleGuard from './ModuleGuard'

function makeUser(role: Role, modules: ModuleKey[]): User {
  return {
    id: 1,
    username: 'u',
    full_name: '测试用户',
    email: null,
    role,
    department: null,
    modules,
    is_active: true,
    must_change_password: false,
  }
}

function renderWithAuth(user: User | null, initialPath: string, children: ReactNode) {
  const value: AuthContextValue = {
    user,
    isAuthenticated: !!user,
    loading: false,
    login: async () => {},
    logout: () => {},
  }
  return render(
    createElement(
      AuthContext.Provider,
      { value },
      createElement(MemoryRouter, { initialEntries: [initialPath] }, children),
    ),
  )
}

const routes = (
  <Routes>
    <Route element={<ModuleGuard module="refstd" />}>
      <Route element={<Outlet />}>
        <Route path="/ref-standards" element={<div>对照品工作区</div>} />
      </Route>
    </Route>
    <Route path="/403" element={<div>无权限页面</div>} />
    <Route path="*" element={<Navigate to="/403" replace />} />
  </Routes>
)

describe('ModuleGuard', () => {
  afterEach(() => cleanup())

  it('renders the workspace when the user has the required module', () => {
    renderWithAuth(makeUser('operator', ['refstd']), '/ref-standards', routes)
    expect(screen.getByText('对照品工作区')).toBeTruthy()
  })

  it('redirects to 403 when the user lacks the module', () => {
    renderWithAuth(makeUser('operator', ['lims']), '/ref-standards', routes)
    expect(screen.getByText('无权限页面')).toBeTruthy()
    expect(screen.queryByText('对照品工作区')).toBeNull()
  })

  it('treats admin as having every module', () => {
    renderWithAuth(makeUser('admin', []), '/ref-standards', routes)
    expect(screen.getByText('对照品工作区')).toBeTruthy()
  })
})
