import type { Id } from './common'

export type UserRole =
  | 'admin'
  | 'director'
  | 'project_manager'
  | 'researcher'
  | 'operator'
  | 'viewer'

/** Backward-compatible name used throughout the existing frontend. */
export type Role = UserRole

/**
 * 工作区模块授权：`lims` 合成实验室工作区，`refstd` 对照品管理工作区。
 * 与后端 UserRead.modules 契约一致（`admin` 账号后端保证返回 ["lims","refstd"]）。
 */
export type ModuleKey = 'lims' | 'refstd'

export interface User {
  id: Id
  username: string
  full_name: string
  email?: string | null
  role: Role
  department?: string | null
  modules: ModuleKey[]
  is_active: boolean
  must_change_password: boolean
}

export interface LoginRequest {
  username: string
  password: string
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface LoginResponse extends AuthTokens {
  user: User
  must_change_password: boolean
}
