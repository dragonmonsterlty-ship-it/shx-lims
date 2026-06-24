import type { ApiEnvelope } from '../types/common'
import { createApiError, normalizeApiError } from './errors'
export { API_MODE, USE_MOCK } from './runtime'

/** 解包统一信封，code!==0 抛出归一化 ApiError。供 mock 与真实路径共用。 */
export function unwrap<T>(env: ApiEnvelope<T>): T {
  if (env.code !== 0) {
    throw createApiError({ code: env.code, message: env.message || '请求失败' })
  }
  return env.data
}

/** 统一把任意异常转为 ApiError，确保 service 层只抛出 ApiError。 */
export function asApiError(error: unknown): never {
  throw normalizeApiError(error)
}
