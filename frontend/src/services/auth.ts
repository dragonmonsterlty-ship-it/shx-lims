import { normalizeModules, normalizeRole } from '../api/adapters'
import { unwrap, USE_MOCK } from '../api/client'
import { endpoints } from '../api/endpoints'
import { request } from '../api/http'
import { mockServer } from '../api/mock'
import {
  clearSession,
  getStoredTokens,
  getStoredUser,
  setStoredTokens,
  setStoredUser,
} from '../api/tokenStore'
import type { Id, LoginRequest, LoginResponse, User } from '../types'

export async function login(req: LoginRequest): Promise<LoginResponse> {
  const res = USE_MOCK
    ? unwrap(await mockServer.auth.login(req.username, req.password))
    : await request<LoginResponse>({ method: 'POST', url: endpoints.auth.login, data: req })
  // real 模式下后端角色词表可能含 pm 等别名，归一到前端角色枚举，确保 RBAC 一致；
  // modules 同步归一（admin 兜底为全部、非法/缺省兜底为 lims）。
  if (!USE_MOCK && res.user) {
    const role = normalizeRole(res.user.role)
    res.user = { ...res.user, role, modules: normalizeModules(res.user.modules, role) }
  }
  setStoredTokens({
    access_token: res.access_token,
    refresh_token: res.refresh_token,
    token_type: res.token_type,
  })
  setStoredUser(res.user)
  return res
}

export function logout(): void {
  const tokens = getStoredTokens()
  if (!USE_MOCK && tokens?.refresh_token) {
    void request({
      method: 'POST',
      url: endpoints.auth.logout,
      data: { refresh_token: tokens.refresh_token },
    }).catch(() => undefined)
  }
  clearSession()
}

export function getCurrentUser(): User | null {
  return getStoredUser()
}

export async function fetchMe(userId: Id): Promise<User> {
  if (USE_MOCK) return unwrap(await mockServer.users.me(userId))
  const me = await request<User>({ method: 'GET', url: endpoints.users.me })
  const role = normalizeRole(me.role)
  return { ...me, role, modules: normalizeModules(me.modules, role) }
}

export const authService = { login, logout, getCurrentUser, fetchMe }
