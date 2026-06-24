import {
  adaptInventoryTransaction,
  adaptReagent,
  adaptReagentLot,
  toBackendReagentCreate,
  toBackendReagentLotCreate,
  toBackendReagentLotUpdate,
  toBackendReagentUpdate,
  type BackendInventoryTransaction,
  type BackendReagent,
  type BackendReagentLot,
} from '../api/adapters'
import { unwrap, USE_MOCK } from '../api/client'
import { createApiError } from '../api/errors'
import { endpoints } from '../api/endpoints'
import { request } from '../api/http'
import { mockServer } from '../api/mock'
import type {
  AdjustInput,
  BatchInput,
  InboundInput,
  InventoryBatch,
  InventoryListQuery,
  InventoryRow,
  InventoryTransaction,
  Id,
  Material,
  NewBatchInput,
  PageResult,
  ReagentInput,
} from '../types'

export async function listMaterials(): Promise<Material[]> {
  if (USE_MOCK) return unwrap(await mockServer.inventory.listMaterials())
  const result = await request<PageResult<BackendReagent>>({
    method: 'GET',
    url: endpoints.reagents.root,
    params: { is_active: true, page_size: 100 },
  })
  return result.items.map(adaptReagent)
}

export async function listAllBatches(): Promise<InventoryBatch[]> {
  if (USE_MOCK) return unwrap(await mockServer.inventory.listAllBatches())
  const result = await request<PageResult<BackendReagentLot>>({
    method: 'GET',
    url: endpoints.reagents.lots,
    params: { page_size: 100 },
  })
  return result.items.map((lot) => adaptReagentLot(lot).batch)
}

export async function listInventory(query: InventoryListQuery): Promise<PageResult<InventoryRow>> {
  if (USE_MOCK) return unwrap(await mockServer.inventory.listRows(query))
  const keyword =
    query.keyword ??
    query.material_code ??
    query.material_name ??
    query.cas_no ??
    query.batch_no ??
    query.supplier ??
    query.location
  const [lots, reagents] = await Promise.all([
    request<PageResult<BackendReagentLot>>({
      method: 'GET',
      url: endpoints.reagents.lots,
      params: {
        keyword,
        status: toBackendLotStatus(query.status),
        low_stock: query.status === 'low' ? true : undefined,
        page: query.page,
        page_size: query.page_size ? Math.min(query.page_size, 100) : undefined,
      },
    }),
    request<PageResult<BackendReagent>>({
      method: 'GET',
      url: endpoints.reagents.root,
      params: { page_size: 100 },
    }),
  ])
  const reagentMap = new Map(reagents.items.map((item) => [item.id, item]))
  return {
    ...lots,
    items: lots.items.map((lot) => adaptReagentLot(lot, reagentMap.get(lot.reagent_id)).row),
  }
}

export async function getBatch(id: Id): Promise<{ batch: InventoryBatch; material: Material | null }> {
  if (USE_MOCK) return unwrap(await mockServer.inventory.getBatch(id))
  const lot = await request<BackendReagentLot>({
    method: 'GET',
    url: endpoints.reagents.lot(id),
  })
  const reagent = await request<BackendReagent>({
    method: 'GET',
    url: endpoints.reagents.detail(lot.reagent_id),
  })
  const result = adaptReagentLot(lot, reagent)
  return { batch: result.batch, material: result.material }
}

export async function listTransactions(batchId: Id): Promise<InventoryTransaction[]> {
  if (USE_MOCK) return unwrap(await mockServer.inventory.listTransactions(batchId))
  const [{ batch }, result] = await Promise.all([
    getBatch(batchId),
    request<PageResult<BackendInventoryTransaction>>({
      method: 'GET',
      url: endpoints.reagents.txns,
      params: { reagent_lot_id: batchId, page_size: 100 },
    }),
  ])
  return result.items.map((item) => ({
    ...adaptInventoryTransaction(item),
    material_id: batch.material_id,
    unit: batch.unit,
  }))
}

export async function listBatchExperiments(batchId: Id) {
  if (USE_MOCK) return unwrap(await mockServer.inventory.listBatchExperiments(batchId))
  return []
}

export async function createReagent(input: ReagentInput): Promise<Material> {
  if (USE_MOCK) throw createApiError({ code: 405, message: 'mock 模式暂不支持试剂主数据创建' })
  return adaptReagent(
    await request<BackendReagent>({
      method: 'POST',
      url: endpoints.reagents.root,
      data: toBackendReagentCreate(input),
    }),
  )
}

export async function updateReagent(id: Id, input: Partial<ReagentInput>): Promise<Material> {
  if (USE_MOCK) throw createApiError({ code: 405, message: 'mock 模式暂不支持试剂主数据编辑' })
  return adaptReagent(
    await request<BackendReagent>({
      method: 'PATCH',
      url: endpoints.reagents.detail(id),
      data: toBackendReagentUpdate(input),
    }),
  )
}

/**
 * 创建批次。最小策略：仅支持「已有试剂(material_id)下建批次」。
 * 初始库存仍通过 inventory-transactions 入库，不绕过流水；
 * 「新建试剂+新批次+初始库存」的一步事务留作后续任务。
 */
export async function createBatch(input: NewBatchInput, actorId: Id): Promise<InventoryBatch> {
  if (USE_MOCK) return unwrap(await mockServer.inventory.createBatch(input, actorId))
  if (input.material_id == null) {
    throw createApiError({
      code: 400,
      message: '请先选择已有试剂再建批次；新建试剂+批次的一步流程待后续任务',
    })
  }
  const created = await request<BackendReagentLot>({
    method: 'POST',
    url: endpoints.reagents.lots,
    data: toBackendReagentLotCreate({
      reagent_id: input.material_id,
      batch_no: input.batch_no,
      quantity: 0,
      unit: input.unit,
      location: input.location,
      expiry_date: input.expiry_date,
      opened_at: input.received_date,
      storage_condition: input.remark,
    }),
  })
  if (input.quantity && input.quantity > 0) {
    await inbound({ batch_id: created.id, qty: input.quantity, reason: '初始入库' }, actorId)
  }
  return (await getBatch(created.id)).batch
}

export async function updateBatch(id: Id, input: Partial<BatchInput>): Promise<InventoryBatch> {
  if (USE_MOCK) throw createApiError({ code: 405, message: 'mock 模式暂不支持批次编辑' })
  await request({
    method: 'PATCH',
    url: endpoints.reagents.lot(id),
    data: toBackendReagentLotUpdate(input),
  })
  return (await getBatch(id)).batch
}

export async function inbound(input: InboundInput, actorId: Id): Promise<InventoryBatch> {
  if (USE_MOCK) return unwrap(await mockServer.inventory.inbound(input, actorId))
  await request({
    method: 'POST',
    url: endpoints.reagents.txns,
    data: {
      reagent_lot_id: input.batch_id,
      txn_type: 'in',
      quantity: input.qty,
      reference: input.reason,
    },
  })
  return (await getBatch(input.batch_id)).batch
}

export async function adjust(input: AdjustInput, actorId: Id): Promise<InventoryBatch> {
  if (USE_MOCK) return unwrap(await mockServer.inventory.adjust(input, actorId))
  const current = (await getBatch(input.batch_id)).batch
  const target = current.quantity + input.qty_delta
  if (target < 0) {
    throw createApiError({ code: 400, message: '调整后库存不能为负' })
  }
  await request({
    method: 'POST',
    url: endpoints.reagents.txns,
    data: {
      reagent_lot_id: input.batch_id,
      txn_type: 'adjust',
      target_quantity: target,
      reference: input.reason,
    },
  })
  return (await getBatch(input.batch_id)).batch
}

export async function setFrozen(batchId: Id, frozen: boolean, actorId: Id): Promise<InventoryBatch> {
  if (USE_MOCK) return unwrap(await mockServer.inventory.setFrozen(batchId, frozen, actorId))
  throw createApiError({ code: 405, message: '当前后端契约不支持冻结/解冻批次' })
}

function toBackendLotStatus(status?: InventoryListQuery['status']): string | undefined {
  if (!status || status === 'low') return undefined
  if (status === 'normal') return 'in_stock'
  if (status === 'frozen') return 'quarantined'
  return status
}

export const inventoryService = {
  listMaterials,
  listAllBatches,
  listInventory,
  getBatch,
  listTransactions,
  listBatchExperiments,
  createReagent,
  updateReagent,
  createBatch,
  updateBatch,
  inbound,
  adjust,
  setFrozen,
}
