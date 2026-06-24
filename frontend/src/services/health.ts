import { unwrap, USE_MOCK } from '../api/client'
import { endpoints } from '../api/endpoints'
import { request } from '../api/http'
import type { ApiEnvelope } from '../types'

export interface HealthStatus {
  status: string
  app?: string
}

export async function checkHealth(): Promise<HealthStatus> {
  if (USE_MOCK) {
    return unwrap<HealthStatus>({
      code: 0,
      message: 'ok',
      data: { status: 'ok', app: 'LIMS Frontend Mock' },
    } satisfies ApiEnvelope<HealthStatus>)
  }
  return request<HealthStatus>({ method: 'GET', url: endpoints.health })
}

export const healthService = { checkHealth }
