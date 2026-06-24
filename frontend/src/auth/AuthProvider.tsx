import { type ReactNode, useCallback, useMemo, useState } from 'react'

import { authService } from '../services/auth'
import type { User } from '../types'
import { AuthContext, type AuthContextValue } from './authContext'

export function AuthProvider({ children }: { children: ReactNode }) {
  // 从本地存储恢复会话（mock）。真实环境可在此 fetchMe 刷新用户。
  const [user, setUser] = useState<User | null>(() => authService.getCurrentUser())

  const login = useCallback(async (username: string, password: string) => {
    const res = await authService.login({ username, password })
    setUser(res.user)
  }, [])

  const logout = useCallback(() => {
    authService.logout()
    setUser(null)
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({ user, isAuthenticated: !!user, loading: false, login, logout }),
    [user, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
