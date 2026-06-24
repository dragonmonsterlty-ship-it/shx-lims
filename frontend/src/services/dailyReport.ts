import {
  adaptDailyReport,
  toBackendDailyReportCreate,
  toBackendDailyReportUpdate,
  type BackendDailyReport,
} from '../api/adapters'
import { unwrap, USE_MOCK } from '../api/client'
import { createApiError } from '../api/errors'
import { endpoints } from '../api/endpoints'
import { request } from '../api/http'
import { mockServer } from '../api/mock'
import type {
  Attachment,
  DailyReport,
  DailyReportActivity,
  DailyReportInput,
  DailyReportListQuery,
  Id,
  PageResult,
  User,
} from '../types'

export async function listReports(
  query: DailyReportListQuery,
  currentUser: User,
): Promise<PageResult<DailyReport>> {
  if (USE_MOCK) return unwrap(await mockServer.dailyReports.list(query, currentUser))
  const result = await request<PageResult<BackendDailyReport>>({
    method: 'GET',
    url: endpoints.dailyReports.root,
    params: {
      user_id: query.user_id,
      project_id: query.project_id,
      experiment_record_id: query.related_experiment_id,
      status: query.status,
      date_from: query.date_from,
      date_to: query.date_to,
      keyword: query.keyword,
      page: query.page,
      page_size: query.page_size ? Math.min(query.page_size, 100) : undefined,
    },
  })
  return { ...result, items: result.items.map(adaptDailyReport) }
}

export async function getReport(id: Id): Promise<DailyReport> {
  if (USE_MOCK) return unwrap(await mockServer.dailyReports.get(id))
  return adaptDailyReport(
    await request<BackendDailyReport>({ method: 'GET', url: endpoints.dailyReports.detail(id) }),
  )
}

export async function createReport(input: DailyReportInput, actorId: Id): Promise<DailyReport> {
  if (USE_MOCK) return unwrap(await mockServer.dailyReports.create(input, actorId))
  return adaptDailyReport(
    await request<BackendDailyReport>({
      method: 'POST',
      url: endpoints.dailyReports.root,
      data: toBackendDailyReportCreate(input),
    }),
  )
}

export async function updateReport(
  id: Id,
  input: Partial<DailyReportInput>,
  actorId: Id,
): Promise<DailyReport> {
  if (USE_MOCK) return unwrap(await mockServer.dailyReports.update(id, input, actorId))
  return adaptDailyReport(
    await request<BackendDailyReport>({
      method: 'PATCH',
      url: endpoints.dailyReports.detail(id),
      data: toBackendDailyReportUpdate(input),
    }),
  )
}

export async function submitReport(id: Id, actorId: Id): Promise<DailyReport> {
  if (USE_MOCK) return unwrap(await mockServer.dailyReports.submit(id, actorId))
  return adaptDailyReport(
    await request<BackendDailyReport>({
      method: 'POST',
      url: endpoints.dailyReports.submit(id),
    }),
  )
}

export async function confirmReport(
  id: Id,
  comment: string | undefined,
  actorId: Id,
): Promise<DailyReport> {
  if (USE_MOCK) return unwrap(await mockServer.dailyReports.confirm(id, comment, actorId))
  return adaptDailyReport(
    await request<BackendDailyReport>({
      method: 'POST',
      url: endpoints.dailyReports.review(id),
      data: { review_comment: comment },
    }),
  )
}

export async function returnReport(id: Id, comment: string, actorId: Id): Promise<DailyReport> {
  if (USE_MOCK) return unwrap(await mockServer.dailyReports.return(id, comment, actorId))
  return adaptDailyReport(
    await request<BackendDailyReport>({
      method: 'POST',
      url: endpoints.dailyReports.return(id),
      data: { review_comment: comment },
    }),
  )
}

export async function listReportActivities(id: Id): Promise<DailyReportActivity[]> {
  if (USE_MOCK) return unwrap(await mockServer.dailyReports.listActivities(id))
  return []
}

export async function listReportAttachments(id: Id): Promise<Attachment[]> {
  if (USE_MOCK) return unwrap(await mockServer.attachments.listByEntity('daily_report', id))
  return (await getReport(id)).attachments ?? []
}

/** 归档日报（real 模式接后端 /archive；mock 暂不支持）。 */
export async function archiveReport(id: Id): Promise<DailyReport> {
  if (USE_MOCK) throw createApiError({ code: 405, message: 'mock 模式暂不支持日报归档' })
  return adaptDailyReport(
    await request<BackendDailyReport>({ method: 'POST', url: endpoints.dailyReports.archive(id) }),
  )
}

export const dailyReportService = {
  listReports,
  getReport,
  createReport,
  updateReport,
  submitReport,
  confirmReport,
  returnReport,
  archiveReport,
  listReportActivities,
  listReportAttachments,
}
