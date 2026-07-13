import { endpoints } from '../api/endpoints'
import { request } from '../api/http'
import type {
  AdminUser,
  AdminUserCreate,
  ModuleKey,
  PasswordResetResult,
  UserRole,
} from '../types'

export function listAdminUsers(): Promise<AdminUser[]> {
  return request<AdminUser[]>({
    method: 'GET',
    url: endpoints.adminUsers.root,
  })
}

export function createAdminUser(payload: AdminUserCreate): Promise<AdminUser> {
  return request<AdminUser>({
    method: 'POST',
    url: endpoints.adminUsers.root,
    data: payload,
  })
}

export function updateUserStatus(userId: number, isActive: boolean): Promise<AdminUser> {
  return request<AdminUser>({
    method: 'PATCH',
    url: endpoints.adminUsers.status(userId),
    data: { is_active: isActive },
  })
}

export function updateUserRole(userId: number, role: UserRole): Promise<AdminUser> {
  return request<AdminUser>({
    method: 'PATCH',
    url: endpoints.adminUsers.role(userId),
    data: { role },
  })
}

export function updateUserModules(userId: number, modules: ModuleKey[]): Promise<AdminUser> {
  return request<AdminUser>({
    method: 'PATCH',
    url: endpoints.adminUsers.modules(userId),
    data: { modules },
  })
}

export function resetUserPassword(
  userId: number,
  newPassword: string,
): Promise<PasswordResetResult> {
  return request<PasswordResetResult>({
    method: 'POST',
    url: endpoints.adminUsers.resetPassword(userId),
    data: { new_password: newPassword },
  })
}

export const adminService = {
  listAdminUsers,
  createAdminUser,
  updateUserStatus,
  updateUserRole,
  updateUserModules,
  resetUserPassword,
}
