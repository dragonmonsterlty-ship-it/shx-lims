import { Navigate, Outlet } from 'react-router-dom'

import { hasModule } from '../auth/modules'
import { useAuth } from '../auth/useAuth'
import type { ModuleKey } from '../types'

/**
 * 模块守卫：无对应工作区模块授权则跳 403（不白屏）。参照 RoleGuard。
 * 模块决定"能进哪个工作区"，与角色（工作区内能做什么）正交；
 * 仅作前端拦截，对照品业务 API 的模块校验以后端为准。
 */
export default function ModuleGuard({ module }: { module: ModuleKey }) {
  const { user } = useAuth()
  if (!user || !hasModule(user, module)) {
    return <Navigate to="/403" replace />
  }
  return <Outlet />
}
