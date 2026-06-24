import {
  adaptProject,
  type BackendProject,
} from '../api/adapters'
import { unwrap, USE_MOCK } from '../api/client'
import { createApiError } from '../api/errors'
import { endpoints } from '../api/endpoints'
import { request } from '../api/http'
import { mockServer } from '../api/mock'
import type {
  Id,
  PageResult,
  Project,
  ProjectInput,
  ProjectListQuery,
  ProjectMember,
  ProjectMemberRole,
  User,
} from '../types'

export async function listProjects(
  query: ProjectListQuery,
  currentUser: User,
): Promise<PageResult<Project>> {
  if (USE_MOCK) return unwrap(await mockServer.projects.list(query, currentUser))
  const result = await request<PageResult<BackendProject>>({
    method: 'GET',
    url: endpoints.projects.root,
    params: {
      keyword: query.keyword ?? query.project_code ?? query.name,
      status: query.status,
      type: query.project_type,
      owner_id: query.lead_user_id,
      priority: query.priority,
      page: query.page,
      page_size: query.page_size ? Math.min(query.page_size, 100) : undefined,
    },
  })
  return { ...result, items: result.items.map(adaptProject) }
}

export async function getProject(id: Id): Promise<Project> {
  if (USE_MOCK) return unwrap(await mockServer.projects.get(id))
  return adaptProject(
    await request<BackendProject>({ method: 'GET', url: endpoints.projects.detail(id) }),
  )
}

export async function createProject(input: ProjectInput, actorId: Id): Promise<Project> {
  if (USE_MOCK) return unwrap(await mockServer.projects.create(input, actorId))
  if (input.lead_user_id == null) {
    throw createApiError({ code: 400, message: '真实后端要求指定项目负责人' })
  }
  const { member_ids: memberIds, ...payload } = input
  const project = adaptProject(
    await request<BackendProject>({
      method: 'POST',
      url: endpoints.projects.root,
      data: payload,
    }),
  )
  await addMissingMembers(project.id, memberIds ?? [], [])
  return getProject(project.id)
}

export async function updateProject(
  id: Id,
  input: Partial<ProjectInput>,
  actorId: Id,
): Promise<Project> {
  if (USE_MOCK) return unwrap(await mockServer.projects.update(id, input, actorId))
  const { member_ids: memberIds, ...payload } = input
  await request<BackendProject>({
    method: 'PATCH',
    url: endpoints.projects.detail(id),
    data: payload,
  })
  if (memberIds) {
    const current = await listMembers(id)
    await addMissingMembers(
      id,
      memberIds,
      current.filter((member) => member.role_in_project === 'member').map((member) => member.user_id),
    )
  }
  return getProject(id)
}

export async function deleteProject(id: Id, actorId: Id): Promise<void> {
  if (USE_MOCK) {
    unwrap(await mockServer.projects.remove(id, actorId))
    return
  }
  await request({ method: 'DELETE', url: endpoints.projects.detail(id) })
}

export async function listMembers(projectId: Id): Promise<ProjectMember[]> {
  if (USE_MOCK) return unwrap(await mockServer.projects.listMembers(projectId))
  return request<ProjectMember[]>({
    method: 'GET',
    url: endpoints.projects.members(projectId),
  })
}

export async function addMember(
  projectId: Id,
  userId: Id,
  role: ProjectMemberRole,
  actorId: Id,
): Promise<ProjectMember> {
  if (USE_MOCK) {
    return unwrap(await mockServer.projects.addMember(projectId, userId, role, actorId))
  }
  return request<ProjectMember>({
    method: 'POST',
    url: endpoints.projects.members(projectId),
    data: { user_id: userId, role_in_project: role },
  })
}

export async function removeMember(projectId: Id, userId: Id): Promise<void> {
  if (USE_MOCK) {
    unwrap(await mockServer.projects.removeMember(projectId, userId))
    return
  }
  await request({ method: 'DELETE', url: endpoints.projects.member(projectId, userId) })
}

export interface MyMemberships {
  managed: Id[]
  member: Id[]
}

/** 当前用户的项目归属：managed=负责的项目，member=参与（含负责）的项目。 */
export async function getMyMemberships(userId: Id): Promise<MyMemberships> {
  if (USE_MOCK) return unwrap(await mockServer.projects.myMemberships(userId))
  const projects = await listProjects({ page_size: 100 }, { id: userId } as User)
  return {
    managed: projects.items
      .filter((project) => project.lead_user_id === userId)
      .map((project) => project.id),
    member: projects.items.map((project) => project.id),
  }
}

async function addMissingMembers(projectId: Id, wanted: Id[], current: Id[]): Promise<void> {
  const wantedSet = new Set(wanted)
  const currentSet = new Set(current)
  await Promise.all(
    current.filter((userId) => !wantedSet.has(userId)).map((userId) => removeMember(projectId, userId)),
  )
  await Promise.all(
    wanted.filter((userId) => !currentSet.has(userId)).map((userId) =>
      addMember(projectId, userId, 'member', 0),
    ),
  )
}

export const projectService = {
  listProjects,
  getProject,
  createProject,
  updateProject,
  deleteProject,
  listMembers,
  addMember,
  removeMember,
  getMyMemberships,
}
