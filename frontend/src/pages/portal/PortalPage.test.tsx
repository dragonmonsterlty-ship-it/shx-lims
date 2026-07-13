// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthContext, type AuthContextValue } from '../../auth/authContext'
import type { ModuleKey, Role, User } from '../../types'
import PortalPage from './PortalPage'

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

function renderPortal(user: User | null): void {
  const value: AuthContextValue = {
    user,
    isAuthenticated: !!user,
    loading: false,
    login: async () => {},
    logout: () => {},
  }
  const tree: ReactNode = createElement(
    AuthContext.Provider,
    { value },
    createElement(
      MemoryRouter,
      { initialEntries: ['/portal'] },
      createElement(
        Routes,
        null,
        createElement(Route, { path: '/portal', element: createElement(PortalPage) }),
        createElement(Route, { path: '/dashboard', element: createElement('div', null, '实验室仪表盘') }),
        createElement(Route, {
          path: '/ref-standards',
          element: createElement('div', null, '对照品台账页'),
        }),
      ),
    ),
  )
  render(tree)
}

describe('PortalPage', () => {
  afterEach(() => cleanup())

  beforeEach(() => {
    window.matchMedia = vi.fn().mockReturnValue({
      matches: false,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })
  })

  it('renders both workspace cards for a user with two modules', () => {
    renderPortal(makeUser('operator', ['lims', 'refstd']))
    expect(screen.getByText('实验室管理')).toBeTruthy()
    expect(screen.getByText('对照品管理')).toBeTruthy()
  })

  it('renders both cards for admin regardless of stored modules', () => {
    renderPortal(makeUser('admin', []))
    expect(screen.getByText('实验室管理')).toBeTruthy()
    expect(screen.getByText('对照品管理')).toBeTruthy()
  })

  it('redirects a single-module user straight into that workspace', () => {
    renderPortal(makeUser('operator', ['lims']))
    expect(screen.getByText('实验室仪表盘')).toBeTruthy()
    expect(screen.queryByText('对照品管理')).toBeNull()
  })

  it('redirects a refstd-only user into the reference-standards workspace', () => {
    renderPortal(makeUser('operator', ['refstd']))
    expect(screen.getByText('对照品台账页')).toBeTruthy()
  })
})
