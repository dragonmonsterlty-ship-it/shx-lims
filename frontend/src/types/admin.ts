import type { UserRole } from './auth'

export interface AdminUser {
  id: number
  username: string
  full_name: string
  email: string | null
  role: UserRole
  department: string | null
  is_active: boolean
  must_change_password: boolean
}

export interface UserStatusUpdate {
  is_active: boolean
}

export interface UserRoleUpdate {
  role: UserRole
}

export interface UserPasswordReset {
  new_password: string
}

export interface PasswordResetResult {
  id: number
  must_change_password: true
}
