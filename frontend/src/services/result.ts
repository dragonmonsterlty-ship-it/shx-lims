import { unwrap } from '../api/client'
import { mockServer } from '../api/mock'
import type { Id, PageResult, Result, ResultReviewQuery, ResultRow, User } from '../types'

export async function listReviewQueue(
  query: ResultReviewQuery,
  currentUser: User,
): Promise<PageResult<ResultRow>> {
  return unwrap(await mockServer.results.reviewList(query, currentUser))
}

export async function reviewResult(
  id: Id,
  action: 'approve' | 'reject',
  comment: string | undefined,
  reviewerId: Id,
): Promise<Result> {
  return unwrap(await mockServer.results.review(id, action, comment, reviewerId))
}

export const resultService = { listReviewQueue, reviewResult }
