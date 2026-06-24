import { Navigate, Outlet } from 'react-router-dom'

import { useAuth } from '../auth/useAuth'
import type { Role } from '../types'

/** 角色守卫：不在允许集合内则跳 403（不白屏）。范围权限仍以后端为准。 */
export default function RoleGuard({ allow }: { allow: Role[] }) {
  const { user } = useAuth()
  if (!user || !allow.includes(user.role)) {
    return <Navigate to="/403" replace />
  }
  return <Outlet />
}
