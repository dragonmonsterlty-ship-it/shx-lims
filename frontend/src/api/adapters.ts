import type {
  Attachment,
  BatchInput,
  DailyReport,
  DailyReportInput,
  DailyReportItemInput,
  Experiment,
  ExperimentInput,
  ExperimentMaterialUsage,
  Id,
  ReagentInput,
  InventoryBatch,
  InventoryRow,
  InventoryTransaction,
  Material,
  Project,
  Role,
  User,
} from '../types'

/**
 * 后端角色词表 → 前端四级角色枚举归一。
 * 后端可能返回 pm / principal_investigator / researcher 等别名；前端 RBAC
 * （菜单、permissions、roleLabel、负责人候选）只认 admin/director/project_manager/operator。
 * 未知角色按最小权限归为 operator，避免越权。
 */
const ROLE_ALIASES: Record<string, Role> = {
  admin: 'admin',
  director: 'director',
  pm: 'project_manager',
  project_manager: 'project_manager',
  principal_investigator: 'project_manager',
  pi: 'project_manager',
  operator: 'operator',
  researcher: 'operator',
  analyst: 'operator',
  qa: 'operator',
}

export function normalizeRole(raw: string | null | undefined): Role {
  if (!raw) return 'operator'
  return ROLE_ALIASES[raw.toLowerCase()] ?? 'operator'
}

export interface BackendUserBrief {
  id: Id
  name?: string
  full_name?: string
  username: string
  role: string
  email?: string | null
  department?: string | null
  is_active?: boolean
  must_change_password?: boolean
}

export interface BackendProject {
  id: Id
  code?: string
  project_code?: string
  name: string
  type?: string | null
  project_type?: string | null
  status: string
  owner?: BackendUserBrief | null
  manager?: BackendUserBrief | null
  lead_user_id?: Id | null
  priority?: string
  description?: string | null
  start_date?: string | null
  expected_end_date?: string | null
  end_date?: string | null
  member_count?: number
  current_stage?: string | null
  progress?: number
  recent_update?: string | null
  risk_summary?: string | null
  next_plan?: string | null
  next_plan_summary?: string | null
  remark?: string | null
  created_by?: Id | null
  created_at?: string
  updated_by?: Id | null
  updated_at?: string | null
  is_deleted?: boolean
}

export interface BackendExperimentUsage {
  id: Id
  experiment_record_id: Id
  reagent_id?: Id | null
  lot_id?: Id | null
  reagent_name_snapshot?: string | null
  lot_code_snapshot?: string | null
  quantity?: number | string | null
  unit?: string | null
  purpose?: string | null
  remark?: string | null
  outbound_status?: ExperimentMaterialUsage['outbound_status']
  shortage_qty?: number | string | null
  stock_available?: number | string | null
}

export interface BackendAttachment {
  id: Id
  experiment_record_id?: Id
  daily_report_id?: Id
  file_name: string
  file_type?: string | null
  file_size?: number | null
  storage_key?: string | null
  uploaded_by?: Id | null
  created_at?: string
}

export interface BackendExperiment {
  id: Id
  code: string
  title: string
  project_id: Id
  project_code: string
  project_name: string
  record_type: string
  status: string
  creator: BackendUserBrief
  owner?: BackendUserBrief | null
  experiment_date?: string | null
  updated_at?: string | null
  attachment_count: number
  reagent_usage_count: number
  creator_id?: Id
  owner_id?: Id | null
  objective?: string | null
  procedure?: string | null
  result_summary?: string | null
  conclusion?: string | null
  next_step?: string | null
  risk_note?: string | null
  reagent_usages?: BackendExperimentUsage[]
  attachments?: BackendAttachment[]
  created_at?: string
  participant_ids?: Id[]
}

export interface BackendDailyReportItem {
  id: Id
  daily_report_id: Id
  project_id?: Id | null
  experiment_record_id?: Id | null
  work_type: string
  content: string
  progress_note?: string | null
  hours_spent?: number | string | null
  problem_note?: string | null
  next_step?: string | null
  sort_order: number
}

export interface BackendDailyReport {
  id: Id
  user: BackendUserBrief
  user_id?: Id
  report_date: string
  status: string
  summary?: string | null
  item_count: number
  project_count: number
  experiment_record_count: number
  submitted_at?: string | null
  reviewed_at?: string | null
  updated_at?: string | null
  reviewer_id?: Id | null
  issues?: string | null
  next_plan?: string | null
  review_comment?: string | null
  items?: BackendDailyReportItem[]
  attachments?: BackendAttachment[]
  created_at?: string
}

export interface BackendReagent {
  id: Id
  name: string
  cas_no?: string | null
  catalog_no?: string | null
  manufacturer?: string | null
  grade?: string | null
  default_unit?: string | null
  min_stock?: number | string | null
  is_active: boolean
  created_by?: Id | null
  created_at?: string
  updated_by?: Id | null
  updated_at?: string | null
}

export interface BackendReagentLot {
  id: Id
  reagent_id: Id
  lot_no: string
  expiry_date?: string | null
  quantity: number | string
  unit?: string | null
  location?: string | null
  storage_condition?: string | null
  opened_at?: string | null
  controlled_flag: boolean
  status: string
}

export interface BackendInventoryTransaction {
  id: Id
  reagent_lot_id: Id
  txn_type: string
  quantity: number | string
  balance_after?: number | string | null
  reference?: string | null
  operator_id?: Id | null
  txn_at: string
  source_type?: 'manual' | 'experiment'
  source_id?: Id | null
  shortage_qty?: number | string | null
}

const toNumber = (value: number | string | null | undefined): number =>
  value == null ? 0 : Number(value)

export function adaptUser(raw: BackendUserBrief): User {
  return {
    id: raw.id,
    username: raw.username,
    full_name: raw.full_name ?? raw.name ?? raw.username,
    email: raw.email ?? null,
    role: normalizeRole(raw.role),
    department: raw.department ?? null,
    is_active: raw.is_active ?? true,
    must_change_password: raw.must_change_password ?? false,
  }
}

export function adaptProject(raw: BackendProject): Project {
  return {
    id: raw.id,
    project_code: raw.project_code ?? raw.code ?? '',
    name: raw.name,
    project_type: raw.project_type ?? raw.type ?? null,
    lead_user_id: raw.lead_user_id ?? raw.owner?.id ?? raw.manager?.id ?? null,
    status: raw.status as Project['status'],
    priority: raw.priority ?? 'normal',
    description: raw.description ?? null,
    start_date: raw.start_date ?? null,
    end_date: raw.end_date ?? raw.expected_end_date ?? null,
    current_stage: raw.current_stage ?? null,
    progress: raw.progress ?? 0,
    recent_update: raw.recent_update ?? null,
    risk_summary: raw.risk_summary ?? null,
    next_plan: raw.next_plan ?? raw.next_plan_summary ?? null,
    remark: raw.remark ?? null,
    member_count: raw.member_count ?? 0,
    is_deleted: raw.is_deleted ?? false,
    created_by: raw.created_by ?? null,
    created_at: raw.created_at,
    updated_by: raw.updated_by ?? null,
    updated_at: raw.updated_at ?? null,
  }
}

function adaptAttachment(
  raw: BackendAttachment,
  entityType: 'experiment' | 'daily_report',
  entityId: Id,
): Attachment {
  return {
    id: raw.id,
    entity_type: entityType,
    entity_id: entityId,
    file_name: raw.file_name,
    storage_key: raw.storage_key ?? '',
    file_type: raw.file_type ?? null,
    content_type_detected: raw.file_type ?? null,
    file_size: raw.file_size ?? null,
    upload_status: 'uploaded',
    preview_status: null,
    uploaded_by: raw.uploaded_by ?? null,
    uploaded_at: raw.created_at ?? '',
  }
}

function adaptExperimentUsage(raw: BackendExperimentUsage): ExperimentMaterialUsage {
  const quantity = raw.quantity == null ? null : toNumber(raw.quantity)
  return {
    id: raw.id,
    experiment_id: raw.experiment_record_id,
    material_id: raw.reagent_id ?? null,
    material_code: '',
    material_name: raw.reagent_name_snapshot ?? '',
    batch_id: raw.lot_id ?? null,
    batch_no: raw.lot_code_snapshot ?? null,
    usage_role: 'reagent',
    planned_qty: quantity,
    actual_qty: quantity,
    unit: raw.unit ?? null,
    stock_available: raw.stock_available == null ? null : toNumber(raw.stock_available),
    stock_status:
      raw.lot_id == null
        ? 'no_stock_link'
        : raw.outbound_status === 'insufficient'
          ? 'insufficient'
          : 'sufficient',
    outbound_status: raw.outbound_status ?? 'pending',
    shortage_qty: raw.shortage_qty == null ? null : toNumber(raw.shortage_qty),
    remark: raw.remark ?? raw.purpose ?? null,
  }
}

export function adaptExperiment(raw: BackendExperiment): Experiment {
  const leadId = raw.owner?.id ?? raw.owner_id ?? raw.creator.id
  return {
    id: raw.id,
    project_id: raw.project_id,
    project_code: raw.project_code,
    project_name: raw.project_name,
    experiment_no: raw.code,
    title: raw.title,
    record_type: raw.record_type,
    lead_user_id: leadId,
    participant_ids: raw.participant_ids ?? [],
    status: raw.status as Experiment['status'],
    experiment_date: raw.experiment_date ?? null,
    plan_start_date: raw.experiment_date ?? null,
    plan_end_date: raw.experiment_date ?? null,
    objective: raw.objective ?? null,
    steps: raw.procedure ?? null,
    result_summary: raw.result_summary ?? null,
    conclusion: raw.conclusion ?? null,
    next_step: raw.next_step ?? null,
    risk_note: raw.risk_note ?? null,
    material_usages: raw.reagent_usages?.map(adaptExperimentUsage) ?? [],
    attachments: raw.attachments?.map((item) => adaptAttachment(item, 'experiment', raw.id)) ?? [],
    attachment_count: raw.attachment_count,
    reagent_usage_count: raw.reagent_usage_count,
    is_deleted: false,
    created_by: raw.creator_id ?? raw.creator.id,
    created_at: raw.created_at,
    updated_at: raw.updated_at ?? null,
  }
}

export function adaptDailyReport(raw: BackendDailyReport): DailyReport {
  const firstItem = raw.items?.[0]
  return {
    id: raw.id,
    user_id: raw.user_id ?? raw.user.id,
    user: adaptUser(raw.user),
    project_id: firstItem?.project_id ?? null,
    related_experiment_id: firstItem?.experiment_record_id ?? null,
    report_date: raw.report_date,
    work_content: raw.summary ?? firstItem?.content ?? '',
    issues_risks: raw.issues ?? firstItem?.problem_note ?? null,
    next_plan: raw.next_plan ?? firstItem?.next_step ?? null,
    status: (raw.status === 'reviewed' ? 'confirmed' : raw.status) as DailyReport['status'],
    submitted_at: raw.submitted_at ?? null,
    reviewed_by: raw.reviewer_id ?? null,
    reviewed_at: raw.reviewed_at ?? null,
    review_comment: raw.review_comment ?? null,
    items: raw.items ?? [],
    attachments: raw.attachments?.map((item) => adaptAttachment(item, 'daily_report', raw.id)) ?? [],
    item_count: raw.item_count,
    project_count: raw.project_count,
    experiment_record_count: raw.experiment_record_count,
    is_deleted: false,
    created_at: raw.created_at,
    updated_at: raw.updated_at ?? null,
  }
}

export function adaptReagent(raw: BackendReagent): Material {
  return {
    id: raw.id,
    material_code: raw.catalog_no ?? `R-${raw.id}`,
    name: raw.name,
    category: 'reagent',
    cas_no: raw.cas_no ?? null,
    specification: raw.grade ?? null,
    unit: raw.default_unit ?? '',
    safety_level: null,
    storage_condition: null,
    is_deleted: !raw.is_active,
    created_by: raw.created_by ?? null,
    created_at: raw.created_at,
    updated_by: raw.updated_by ?? null,
    updated_at: raw.updated_at ?? null,
  }
}

const adaptBatchStatus = (status: string): InventoryBatch['status'] => {
  if (status === 'in_stock') return 'normal'
  if (status === 'quarantined') return 'frozen'
  return status as InventoryBatch['status']
}

export function adaptReagentLot(
  raw: BackendReagentLot,
  reagent?: BackendReagent,
): { batch: InventoryBatch; material: Material | null; row: InventoryRow } {
  const material = reagent ? adaptReagent(reagent) : null
  const quantity = toNumber(raw.quantity)
  const minStock = reagent?.min_stock == null ? null : toNumber(reagent.min_stock)
  const status =
    raw.status === 'in_stock' && minStock != null && quantity < minStock
      ? 'low'
      : adaptBatchStatus(raw.status)
  const batch: InventoryBatch = {
    id: raw.id,
    material_id: raw.reagent_id,
    batch_no: raw.lot_no,
    supplier: reagent?.manufacturer ?? null,
    purity: reagent?.grade ?? null,
    location: raw.location ?? null,
    quantity,
    unit: raw.unit ?? reagent?.default_unit ?? '',
    received_date: raw.opened_at ?? null,
    expiry_date: raw.expiry_date ?? null,
    status,
    remark: raw.storage_condition ?? null,
  }
  return {
    batch,
    material,
    row: {
      batch_id: batch.id,
      material_id: batch.material_id,
      material_code: material?.material_code ?? `R-${raw.reagent_id}`,
      material_name: material?.name ?? `试剂 #${raw.reagent_id}`,
      category: 'reagent',
      cas_no: material?.cas_no ?? null,
      batch_no: batch.batch_no,
      supplier: batch.supplier,
      location: batch.location,
      quantity: batch.quantity,
      unit: batch.unit,
      expiry_date: batch.expiry_date,
      status: batch.status,
    },
  }
}

export function adaptInventoryTransaction(
  raw: BackendInventoryTransaction,
): InventoryTransaction {
  const quantity = toNumber(raw.quantity)
  const transactionType =
    raw.txn_type === 'in'
      ? 'inbound'
      : raw.txn_type === 'out'
        ? 'outbound'
        : 'adjustment'
  return {
    id: raw.id,
    material_id: 0,
    batch_id: raw.reagent_lot_id,
    transaction_type: transactionType,
    qty_delta: raw.txn_type === 'out' ? -Math.abs(quantity) : quantity,
    unit: '',
    source_type: raw.source_type ?? 'manual',
    source_id: raw.source_id ?? null,
    actor_id: raw.operator_id ?? null,
    at: raw.txn_at,
    reason: raw.reference ?? null,
    balance_after: raw.balance_after == null ? null : toNumber(raw.balance_after),
  }
}

// ---------- 实验写路径：前端 ExperimentInput → 后端 experiment-records 载荷 ----------

const DEFAULT_RECORD_TYPE = 'other'

function stepsToProcedure(steps: string | string[] | null | undefined): string | null {
  if (steps == null) return null
  return Array.isArray(steps) ? steps.filter(Boolean).join('\n') : steps
}

function experimentDate(input: Pick<ExperimentInput, 'plan_start_date' | 'plan_end_date'>): string | null {
  return input.plan_start_date ?? input.plan_end_date ?? null
}

export interface BackendExperimentCreatePayload {
  project_id: Id
  code: string
  title: string
  record_type: string
  status?: string
  owner_id?: Id | null
  experiment_date?: string | null
  objective?: string | null
  procedure?: string | null
  result_summary?: string | null
  conclusion?: string | null
  next_step?: string | null
  risk_note?: string | null
  participant_ids: Id[]
  reagent_usages: Record<string, unknown>[]
}

function toBackendExperimentUsages(input: ExperimentInput['material_usages']): Record<string, unknown>[] {
  return (input ?? []).map((usage) => ({
    lot_id: usage.batch_id ?? null,
    quantity: usage.actual_qty ?? usage.planned_qty ?? null,
    purpose: usage.usage_role,
    remark: usage.remark ?? null,
  }))
}

/**
 * 创建实验记录映射：
 * - experiment_no → code（为空时按时间戳生成，避免空）
 * - lead_user_id → owner_id；participant_ids 写入参与人关联表
 * - 计划起/止日期 → 单一 experiment_date（取起始优先）
 * - steps（文本/数组）→ procedure 文本
 * - record_type 缺省取安全默认值 'other'
 */
export function toBackendExperimentCreate(input: ExperimentInput): BackendExperimentCreatePayload {
  return {
    project_id: input.project_id,
    code: input.experiment_no?.trim() || `EXP-${Date.now()}`,
    title: input.title,
    record_type: input.record_type?.trim() || DEFAULT_RECORD_TYPE,
    status: input.status,
    owner_id: input.lead_user_id ?? null,
    experiment_date: experimentDate(input),
    objective: input.objective ?? null,
    procedure: stepsToProcedure(input.steps),
    result_summary: input.result_summary ?? null,
    conclusion: input.conclusion ?? null,
    next_step: input.next_step ?? null,
    risk_note: input.risk_note ?? null,
    participant_ids: input.participant_ids ?? [],
    reagent_usages: toBackendExperimentUsages(input.material_usages),
  }
}

/** 更新实验记录映射：仅包含传入字段（PATCH 语义）。 */
export function toBackendExperimentUpdate(
  input: Partial<ExperimentInput>,
): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  if (input.experiment_no !== undefined) out.code = input.experiment_no?.trim() || undefined
  if (input.title !== undefined) out.title = input.title
  if (input.record_type !== undefined) out.record_type = input.record_type
  if (input.status !== undefined) out.status = input.status
  if (input.lead_user_id !== undefined) out.owner_id = input.lead_user_id
  if (input.plan_start_date !== undefined || input.plan_end_date !== undefined) {
    out.experiment_date = experimentDate(input)
  }
  if (input.objective !== undefined) out.objective = input.objective
  if (input.steps !== undefined) out.procedure = stepsToProcedure(input.steps)
  if (input.result_summary !== undefined) out.result_summary = input.result_summary
  if (input.conclusion !== undefined) out.conclusion = input.conclusion
  if (input.next_step !== undefined) out.next_step = input.next_step
  if (input.risk_note !== undefined) out.risk_note = input.risk_note
  if (input.participant_ids !== undefined) out.participant_ids = input.participant_ids
  if (input.material_usages !== undefined) out.reagent_usages = toBackendExperimentUsages(input.material_usages)
  return out
}

// ---------- 试剂/批次写路径：前端 Material/Batch → 后端 reagents / reagent-lots ----------

function lotStatusToBackend(status?: InventoryBatch['status']): string {
  if (status === 'frozen') return 'quarantined'
  // normal/low/depleted/expired 等前端态创建时统一落为 in_stock（低库存为派生、非存储态）
  return 'in_stock'
}

/** 创建试剂：material_code→catalog_no、specification→grade、unit→default_unit；后端无的前端字段不写入。 */
export function toBackendReagentCreate(input: ReagentInput): Record<string, unknown> {
  return {
    name: input.name,
    cas_no: input.cas_no ?? null,
    catalog_no: input.material_code ?? null,
    grade: input.specification ?? null,
    default_unit: input.unit ?? null,
    manufacturer: input.manufacturer ?? null,
    min_stock: input.min_stock ?? null,
    is_active: input.is_active ?? true,
  }
}

/** 更新试剂：仅含传入字段（PATCH）。 */
export function toBackendReagentUpdate(input: Partial<ReagentInput>): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  if (input.name !== undefined) out.name = input.name
  if (input.cas_no !== undefined) out.cas_no = input.cas_no
  if (input.material_code !== undefined) out.catalog_no = input.material_code
  if (input.specification !== undefined) out.grade = input.specification
  if (input.unit !== undefined) out.default_unit = input.unit
  if (input.manufacturer !== undefined) out.manufacturer = input.manufacturer
  if (input.min_stock !== undefined) out.min_stock = input.min_stock
  if (input.is_active !== undefined) out.is_active = input.is_active
  return out
}

/** 创建批次：batch_no→lot_no、opened_at/storage_condition 直传；status 归一为后端值。 */
export function toBackendReagentLotCreate(input: BatchInput): Record<string, unknown> {
  return {
    reagent_id: input.reagent_id,
    lot_no: input.batch_no,
    quantity: input.quantity ?? 0,
    unit: input.unit ?? null,
    location: input.location ?? null,
    expiry_date: input.expiry_date ?? null,
    opened_at: input.opened_at ?? null,
    storage_condition: input.storage_condition ?? null,
    controlled_flag: input.controlled_flag ?? false,
    status: lotStatusToBackend(input.status),
  }
}

/** 更新批次：仅含传入字段（PATCH）；**不含 quantity**（库存量改动走 inventory-transactions）。 */
export function toBackendReagentLotUpdate(input: Partial<BatchInput>): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  if (input.batch_no !== undefined) out.lot_no = input.batch_no
  if (input.unit !== undefined) out.unit = input.unit
  if (input.location !== undefined) out.location = input.location
  if (input.expiry_date !== undefined) out.expiry_date = input.expiry_date
  if (input.opened_at !== undefined) out.opened_at = input.opened_at
  if (input.storage_condition !== undefined) out.storage_condition = input.storage_condition
  if (input.controlled_flag !== undefined) out.controlled_flag = input.controlled_flag
  if (input.status !== undefined) out.status = lotStatusToBackend(input.status)
  return out
}

// ---------- 日报写路径：前端扁平/多条 → 后端 daily-reports items[] ----------

function buildDailyReportItem(item: DailyReportItemInput, index: number): Record<string, unknown> {
  return {
    project_id: item.project_id ?? null,
    experiment_record_id: item.experiment_record_id ?? null,
    work_type: item.work_type?.trim() || 'other',
    content: item.content ?? '',
    progress_note: item.progress_note ?? null,
    hours_spent: item.hours_spent ?? null,
    problem_note: item.problem_note ?? null,
    next_step: item.next_step ?? null,
    sort_order: item.sort_order ?? index,
  }
}

/** 扁平字段 → 单条后端 item（兼容旧单条表单）。 */
function flatToDailyReportItems(input: Partial<DailyReportInput>): Record<string, unknown>[] {
  return [
    buildDailyReportItem(
      {
        project_id: input.project_id ?? null,
        experiment_record_id: input.related_experiment_id ?? null,
        work_type: 'other',
        content: input.work_content ?? '',
        problem_note: input.issues_risks ?? null,
        next_step: input.next_plan ?? null,
      },
      0,
    ),
  ]
}

/** 创建日报：顶层 summary/issues/next_plan + items[]（多条优先，否则扁平转单条）。 */
export function toBackendDailyReportCreate(input: DailyReportInput): Record<string, unknown> {
  const items = input.items?.length ? input.items.map(buildDailyReportItem) : flatToDailyReportItems(input)
  return {
    report_date: input.report_date,
    summary: input.work_content ?? input.items?.[0]?.content ?? null,
    issues: input.issues_risks ?? input.items?.[0]?.problem_note ?? null,
    next_plan: input.next_plan ?? input.items?.[0]?.next_step ?? null,
    items,
  }
}

/** 更新日报：PATCH 语义，仅含传入字段；显式 items 优先，否则扁平变更同步为单条 item。 */
export function toBackendDailyReportUpdate(input: Partial<DailyReportInput>): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  if (input.report_date !== undefined) out.report_date = input.report_date
  if (input.work_content !== undefined) out.summary = input.work_content
  if (input.issues_risks !== undefined) out.issues = input.issues_risks
  if (input.next_plan !== undefined) out.next_plan = input.next_plan
  if (input.items !== undefined) {
    out.items = input.items.map(buildDailyReportItem)
    out.summary = input.items[0]?.content ?? null
    out.issues = input.items[0]?.problem_note ?? null
    out.next_plan = input.items[0]?.next_step ?? null
  } else if (
    input.work_content !== undefined ||
    input.project_id !== undefined ||
    input.related_experiment_id !== undefined
  ) {
    out.items = flatToDailyReportItems(input)
  }
  return out
}
