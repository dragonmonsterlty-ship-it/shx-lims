import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'

import { userService } from '../services/user'
import type { Id, User } from '../types'

/**
 * 用户字典。用于把 user_id 解析为姓名（列表/详情展示）。
 * 数据源为 userService.listUsers（真实后端缺列表端点时由 mock 提供）。
 */
export function useUsers() {
  const query = useQuery({ queryKey: ['users'], queryFn: () => userService.listUsers() })

  const map = useMemo(() => {
    const m = new Map<Id, User>()
    for (const u of query.data ?? []) m.set(u.id, u)
    return m
  }, [query.data])

  const getName = (id?: Id | null): string => {
    if (id == null) return '—'
    return map.get(id)?.full_name ?? `#${id}`
  }

  return { ...query, map, getName }
}
