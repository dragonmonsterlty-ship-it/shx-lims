import { adaptTestResult, type BackendTestResult } from '../api/adapters'
import { endpoints } from '../api/endpoints'
import { request } from '../api/http'
import type {
  Id,
  PageResult,
  Result,
  ResultDraftInput,
  ResultReviewQuery,
  ResultRow,
  User,
} from '../types'

export async function listReviewQueue(
  query: ResultReviewQuery,
  currentUser: User,
): Promise<PageResult<ResultRow>> {
  void currentUser
  const result = await request<PageResult<BackendTestResult>>({
    method: 'GET',
    url: endpoints.results.root,
    params: {
      project_id: query.project_id,
      status: query.review_status,
      page: query.page,
      page_size: query.page_size,
    },
  })
  return { ...result, items: result.items.map(adaptTestResult) }
}

export async function getResult(id: Id): Promise<Result> {
  return adaptTestResult(
    await request<BackendTestResult>({ method: 'GET', url: endpoints.results.detail(id) }),
  )
}

export async function saveDraft(
  taskId: Id,
  input: ResultDraftInput,
  existingResultId?: Id | null,
): Promise<Result> {
  const result = await request<BackendTestResult>({
    method: existingResultId ? 'PATCH' : 'POST',
    url: existingResultId ? endpoints.results.detail(existingResultId) : endpoints.results.root,
    data: existingResultId ? input : { task_id: taskId, ...input },
  })
  return adaptTestResult(result)
}

export async function submitResult(id: Id): Promise<Result> {
  return adaptTestResult(
    await request<BackendTestResult>({ method: 'POST', url: endpoints.results.submit(id) }),
  )
}

export async function reviewResult(
  id: Id,
  action: 'approve' | 'reject',
  comment?: string,
  reviewerId?: Id,
): Promise<Result> {
  void reviewerId
  const url = action === 'approve' ? endpoints.results.approve(id) : endpoints.results.reject(id)
  return adaptTestResult(
    await request<BackendTestResult>({ method: 'POST', url, data: { comment } }),
  )
}

export const resultService = { listReviewQueue, getResult, saveDraft, submitResult, reviewResult }
