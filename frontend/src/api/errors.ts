import { AxiosError } from 'axios'

import type { ApiEnvelope } from '../types/common'

/** 归一化后的前端错误对象，页面据此给出可恢复提示。 */
export interface ApiError {
  code: number
  message: string
  status?: number
  fieldErrors?: Record<string, string>
  isNetwork?: boolean
  raw?: unknown
}

export function createApiError(partial: Partial<ApiError> & { message: string }): ApiError {
  return { code: partial.code ?? -1, ...partial }
}

export function isApiError(value: unknown): value is ApiError {
  return (
    typeof value === 'object' &&
    value !== null &&
    'message' in value &&
    'code' in value &&
    typeof (value as { code?: unknown }).code === 'number'
  )
}

/** 将 axios / 信封 / 未知错误统一转换为 ApiError，绝不抛出原始异常给页面。 */
export function normalizeApiError(error: unknown): ApiError {
  if (isApiError(error)) return error

  if (error instanceof AxiosError) {
    if (error.response) {
      const body = error.response.data as Partial<ApiEnvelope<unknown>> | undefined
      const fieldErrors = extractFieldErrors(body?.data)
      return {
        code: body?.code ?? error.response.status,
        status: error.response.status,
        message: body?.message || error.message || '请求失败',
        fieldErrors,
        raw: error,
      }
    }
    return {
      code: -1,
      isNetwork: true,
      message: '无法连接后端 API，请检查服务地址或服务状态',
      raw: error,
    }
  }

  if (error instanceof Error) {
    return { code: -1, message: error.message, raw: error }
  }

  return { code: -1, message: '未知错误', raw: error }
}

function extractFieldErrors(data: unknown): Record<string, string> | undefined {
  if (!data || typeof data !== 'object' || !('errors' in data)) return undefined
  const errors = (data as { errors?: unknown }).errors
  if (!Array.isArray(errors)) return undefined
  const out: Record<string, string> = {}
  for (const item of errors) {
    if (item && typeof item === 'object' && 'loc' in item && 'msg' in item) {
      const loc = (item as { loc?: unknown[] }).loc
      const key = Array.isArray(loc) ? String(loc[loc.length - 1]) : 'non_field'
      out[key] = String((item as { msg?: unknown }).msg ?? '校验失败')
    }
  }
  return Object.keys(out).length ? out : undefined
}
