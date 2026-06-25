import { adaptUser, type BackendUserBrief } from '../api/adapters'
import { unwrap, USE_MOCK } from '../api/client'
import { endpoints } from '../api/endpoints'
import { request } from '../api/http'
import { mockServer } from '../api/mock'
import type { User } from '../types'

export async function listUsers(): Promise<User[]> {
  if (USE_MOCK) return unwrap(await mockServer.users.list())
  const users = await request<BackendUserBrief[]>({ method: 'GET', url: endpoints.users.list })
  return users.map(adaptUser)
}

export async function listProjectOwnerCandidates(keyword?: string): Promise<User[]> {
  if (USE_MOCK) {
    const users = unwrap(await mockServer.users.list())
    return users.filter((user) =>
      ['admin', 'project_manager'].includes(user.role),
    )
  }
  const users = await request<BackendUserBrief[]>({
    method: 'GET',
    url: endpoints.users.projectOwnerCandidates,
    params: { keyword },
  })
  return users.map(adaptUser)
}

export const userService = { listUsers, listProjectOwnerCandidates }
