import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'

import type { ProjectScope } from '../auth/permissions'
import { projectService } from '../services/project'
import type { User } from '../types'

/** 当前用户的项目归属（managed/member 集合），用于实验等模块的行级权限判断。 */
export function useProjectScope(user: User | null): { scope: ProjectScope; isLoading: boolean } {
  const query = useQuery({
    queryKey: ['myMemberships', user?.id],
    queryFn: () => projectService.getMyMemberships(user!.id),
    enabled: !!user,
  })

  const scope = useMemo<ProjectScope>(
    () => ({
      managed: new Set(query.data?.managed ?? []),
      member: new Set(query.data?.member ?? []),
    }),
    [query.data],
  )

  return { scope, isLoading: query.isLoading }
}
