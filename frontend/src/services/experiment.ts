import {
  adaptExperiment,
  toBackendExperimentCreate,
  toBackendExperimentUpdate,
  type BackendExperiment,
} from '../api/adapters'
import { unwrap, USE_MOCK } from '../api/client'
import { createApiError } from '../api/errors'
import { endpoints } from '../api/endpoints'
import { request } from '../api/http'
import { mockServer } from '../api/mock'
import { listAttachments } from './attachment'
import type {
  Attachment,
  Experiment,
  ExperimentActivity,
  ExperimentInput,
  ExperimentListQuery,
  ExperimentMaterialUsage,
  Id,
  PageResult,
  User,
} from '../types'

export async function listExperiments(
  query: ExperimentListQuery,
  currentUser: User,
): Promise<PageResult<Experiment>> {
  if (USE_MOCK) return unwrap(await mockServer.experiments.list(query, currentUser))
  const result = await request<PageResult<BackendExperiment>>({
    method: 'GET',
    url: endpoints.experiments.root,
    params: {
      project_id: query.project_id,
      keyword: query.keyword ?? query.experiment_no ?? query.title,
      status: query.status,
      owner_id: query.lead_user_id,
      date_from: query.plan_date_from,
      date_to: query.plan_date_to,
      page: query.page,
      page_size: query.page_size ? Math.min(query.page_size, 100) : undefined,
    },
  })
  return { ...result, items: result.items.map(adaptExperiment) }
}

export async function getExperiment(id: Id): Promise<Experiment> {
  if (USE_MOCK) return unwrap(await mockServer.experiments.get(id))
  return adaptExperiment(
    await request<BackendExperiment>({ method: 'GET', url: endpoints.experiments.detail(id) }),
  )
}

export async function createExperiment(input: ExperimentInput, actorId: Id): Promise<Experiment> {
  if (USE_MOCK) return unwrap(await mockServer.experiments.create(input, actorId))
  return adaptExperiment(
    await request<BackendExperiment>({
      method: 'POST',
      url: endpoints.experiments.root,
      data: toBackendExperimentCreate(input),
    }),
  )
}

export async function updateExperiment(
  id: Id,
  input: Partial<ExperimentInput>,
  actorId: Id,
): Promise<Experiment> {
  if (USE_MOCK) return unwrap(await mockServer.experiments.update(id, input, actorId))
  return adaptExperiment(
    await request<BackendExperiment>({
      method: 'PATCH',
      url: endpoints.experiments.detail(id),
      data: toBackendExperimentUpdate(input),
    }),
  )
}

/** 提交实验记录（real 模式接后端 /submit；mock 暂不支持）。 */
export async function submitExperiment(id: Id): Promise<Experiment> {
  if (USE_MOCK) throw createApiError({ code: 405, message: 'mock 模式暂不支持实验提交' })
  return adaptExperiment(
    await request<BackendExperiment>({ method: 'POST', url: endpoints.experiments.submit(id) }),
  )
}

/** 归档实验记录（real 模式接后端 /archive；mock 暂不支持）。 */
export async function archiveExperiment(id: Id): Promise<Experiment> {
  if (USE_MOCK) throw createApiError({ code: 405, message: 'mock 模式暂不支持实验归档' })
  return adaptExperiment(
    await request<BackendExperiment>({ method: 'POST', url: endpoints.experiments.archive(id) }),
  )
}

export async function deleteExperiment(id: Id, actorId: Id): Promise<void> {
  if (USE_MOCK) {
    unwrap(await mockServer.experiments.remove(id, actorId))
    return
  }
  throw createApiError({ code: 405, message: '当前后端契约不支持删除实验记录' })
}

export async function listExperimentActivities(id: Id): Promise<ExperimentActivity[]> {
  if (USE_MOCK) return unwrap(await mockServer.experiments.listActivities(id))
  return []
}

export async function listExperimentAttachments(id: Id): Promise<Attachment[]> {
  return listAttachments('experiment', id)
}

export async function listMaterialUsages(id: Id): Promise<ExperimentMaterialUsage[]> {
  if (USE_MOCK) return unwrap(await mockServer.experiments.listMaterialUsages(id))
  return (await getExperiment(id)).material_usages ?? []
}

export async function dispenseMaterials(
  id: Id,
  actorId: Id,
): Promise<ExperimentMaterialUsage[]> {
  if (USE_MOCK) return unwrap(await mockServer.experiments.dispenseMaterials(id, actorId))
  const experiment = adaptExperiment(
    await request<BackendExperiment>({
      method: 'POST',
      url: endpoints.experiments.dispense(id),
    }),
  )
  return experiment.material_usages ?? []
}

export const experimentService = {
  listExperiments,
  getExperiment,
  createExperiment,
  updateExperiment,
  submitExperiment,
  archiveExperiment,
  deleteExperiment,
  listExperimentActivities,
  listExperimentAttachments,
  listMaterialUsages,
  dispenseMaterials,
}
