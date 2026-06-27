import { endpoints } from '../api/endpoints'
import { request } from '../api/http'
import type { AuditLog, AuditLogListData, AuditLogListQuery } from '../types'

function definedQuery(query: AuditLogListQuery): AuditLogListQuery {
  return Object.fromEntries(
    Object.entries(query).filter(([, value]) => value !== undefined && value !== null),
  ) as AuditLogListQuery
}

export function listAuditLogs(query: AuditLogListQuery = {}): Promise<AuditLogListData> {
  return request<AuditLogListData>({
    method: 'GET',
    url: endpoints.auditLogs.root,
    params: definedQuery(query),
  })
}

export function getEntityAuditTimeline(
  entityType: string,
  entityId: number,
): Promise<AuditLog[]> {
  return request<AuditLog[]>({
    method: 'GET',
    url: endpoints.auditLogs.entity(entityType, entityId),
  })
}

export const auditService = { listAuditLogs, getEntityAuditTimeline }
