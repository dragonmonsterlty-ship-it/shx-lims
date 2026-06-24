import axios, { type AxiosRequestConfig } from 'axios'

import type { ApiEnvelope } from '../types/common'
import { createApiError, normalizeApiError } from './errors'
import { getStoredTokens } from './tokenStore'

export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/+$/, '') ??
  'http://127.0.0.1:18000/api'

/**
 * 真实后端 axios 实例。API base URL 只在这里读取，页面和 service 不硬编码地址。
 */
export const httpClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
})

httpClient.interceptors.request.use((config) => {
  const tokens = getStoredTokens()
  if (tokens?.access_token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${tokens.access_token}`
  }
  return config
})

/** 解包统一信封，code!==0 抛出归一化 ApiError。 */
export async function request<T>(config: AxiosRequestConfig): Promise<T> {
  try {
    const response = await httpClient.request<ApiEnvelope<T>>(config)
    const body = response.data
    if (body.code !== 0) {
      throw createApiError({ code: body.code, message: body.message || '请求失败' })
    }
    return body.data
  } catch (error) {
    throw normalizeApiError(error)
  }
}
