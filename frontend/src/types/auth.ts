import type { Id } from './common'

/** 兼容 T1.1 后端当前角色集合；权限真相仍以后端为准。 */
export type Role =
  | 'admin'
  | 'director'
  | 'pm'
  | 'project_manager'
  | 'principal_investigator'
  | 'researcher'
  | 'analyst'
  | 'operator'
  | 'qa'

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
