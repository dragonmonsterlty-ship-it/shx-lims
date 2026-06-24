import type { AuditFields, Id } from './common'

export type MaterialCategory =
  | 'starting_material'
  | 'reagent'
  | 'solvent'
  | 'catalyst'
  | 'standard'
  | 'consumable'
  | 'intermediate'
  | 'product'

export type BatchStatus = 'normal' | 'low' | 'depleted' | 'expired' | 'frozen'
export type TransactionType = 'inbound' | 'outbound' | 'adjustment' | 'return'

export interface Material extends AuditFields {
  id: Id
  material_code: string
  name: string
  category: MaterialCategory
  cas_no?: string | null
  specification?: string | null
  unit: string
  safety_level?: string | null
  storage_condition?: string | null
  is_deleted: boolean
}

export interface InventoryBatch {
  id: Id
  material_id: Id
  batch_no: string
  supplier?: string | null
  purity?: string | null
  location?: string | null
  quantity: number
  unit: string
  received_date?: string | null
  expiry_date?: string | null
  status: BatchStatus
  remark?: string | null
}

export interface InventoryTransaction {
  id: Id
  material_id: Id
  batch_id: Id
  transaction_type: TransactionType
  /** 入库为正，出库为负。 */
  qty_delta: number
  unit: string
  source_type: 'manual' | 'experiment'
  source_id?: Id | null
  actor_id?: Id | null
  at: string
  reason?: string | null
  balance_after?: number | null
}

/** 列表扁平行（批次 join 物料）。 */
export interface InventoryRow {
  batch_id: Id
  material_id: Id
  material_code: string
  material_name: string
  category: MaterialCategory
  cas_no?: string | null
  batch_no: string
  supplier?: string | null
  location?: string | null
  quantity: number
  unit: string
  expiry_date?: string | null
  status: BatchStatus
}

export interface InventoryListQuery {
  page?: number
  page_size?: number
  keyword?: string
  material_code?: string
  material_name?: string
  cas_no?: string
  category?: MaterialCategory
  batch_no?: string
  supplier?: string
  location?: string
  status?: BatchStatus
}

export interface NewBatchInput {
  /** 选择已有物料；为空则用下方字段新建物料。 */
  material_id?: Id
  material_code?: string
  name?: string
  category?: MaterialCategory
  cas_no?: string | null
  specification?: string | null
  unit: string
  safety_level?: string | null
  storage_condition?: string | null
  // 批次
  batch_no: string
  supplier?: string | null
  purity?: string | null
  location?: string | null
  quantity: number
  received_date?: string | null
  expiry_date?: string | null
  remark?: string | null
}

/** 试剂主数据写入（前端 Material 概念 → 后端 Reagent）。 */
export interface ReagentInput {
  name: string
  material_code?: string | null
  cas_no?: string | null
  specification?: string | null
  unit?: string | null
  manufacturer?: string | null
  min_stock?: number | null
  is_active?: boolean
}

/** 批次写入（前端 Batch 概念 → 后端 ReagentLot）。需已有 reagent_id。 */
export interface BatchInput {
  reagent_id: Id
  batch_no: string
  quantity?: number
  unit?: string | null
  location?: string | null
  expiry_date?: string | null
  opened_at?: string | null
  storage_condition?: string | null
  controlled_flag?: boolean
  status?: BatchStatus
}

export interface InboundInput {
  batch_id: Id
  qty: number
  reason?: string | null
}

export interface AdjustInput {
  batch_id: Id
  qty_delta: number
  reason?: string | null
}
