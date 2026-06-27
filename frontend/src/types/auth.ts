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

export interface User {
  id: Id
  username: string
  full_name: string
  email?: string | null
  role: Role
  department?: string | null
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
