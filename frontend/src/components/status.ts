// 状态枚举 → 颜色 + 中文标签的统一映射。
// sample 与 judgment 颜色遵循 CLAUDE.md 固定规则；其余按同一色板延伸。

export type StatusKind =
  | 'sample'
  | 'test'
  | 'daily_report'
  | 'experiment'
  | 'review'
  | 'judgment'
  | 'project'
  | 'lot'
  | 'material_stock'
  | 'dispense'
  | 'batch'

export interface StatusMeta {
  color: string
  label: string
}

const MAPS: Record<StatusKind, Record<string, StatusMeta>> = {
  sample: {
    registered: { color: 'default', label: '已登记' },
    in_testing: { color: 'blue', label: '检测中' },
    pending_review: { color: 'orange', label: '待审核' },
    completed: { color: 'green', label: '已完成' },
    cancelled: { color: 'red', label: '已作废' },
  },
  test: {
    pending: { color: 'default', label: '待检' },
    in_progress: { color: 'blue', label: '检测中' },
    done: { color: 'green', label: '已出结果' },
  },
  daily_report: {
    draft: { color: 'default', label: '草稿' },
    submitted: { color: 'orange', label: '已提交' },
    returned: { color: 'red', label: '已退回' },
    reviewed: { color: 'green', label: '已审核' },
    archived: { color: 'default', label: '已归档' },
    confirmed: { color: 'green', label: '已确认' },
  },
  experiment: {
    draft: { color: 'default', label: '草稿' },
    planned: { color: 'cyan', label: '计划中' },
    in_progress: { color: 'blue', label: '进行中' },
    submitted: { color: 'orange', label: '已提交' },
    reviewed: { color: 'green', label: '已审核' },
    archived: { color: 'default', label: '已归档' },
    completed: { color: 'green', label: '已完成' },
    cancelled: { color: 'red', label: '已取消' },
  },
  review: {
    pending: { color: 'orange', label: '待审' },
    approved: { color: 'green', label: '通过' },
    rejected: { color: 'red', label: '退回' },
  },
  judgment: {
    pass: { color: 'green', label: '合格' },
    fail: { color: 'red', label: '不合格' },
    oos: { color: 'red', label: '超标 OOS' },
  },
  project: {
    active: { color: 'blue', label: '进行中' },
    paused: { color: 'orange', label: '暂停' },
    completed: { color: 'green', label: '已完成' },
    cancelled: { color: 'red', label: '已终止' },
  },
  lot: {
    in_stock: { color: 'green', label: '在库' },
    depleted: { color: 'default', label: '用尽' },
    expired: { color: 'red', label: '过期' },
    quarantined: { color: 'orange', label: '隔离' },
  },
  material_stock: {
    sufficient: { color: 'green', label: '充足' },
    insufficient: { color: 'red', label: '不足' },
    no_stock_link: { color: 'default', label: '未关联库存' },
  },
  dispense: {
    pending: { color: 'default', label: '未出库' },
    dispensed: { color: 'green', label: '已出库' },
    insufficient: { color: 'red', label: '库存不足' },
    revoked: { color: 'orange', label: '已撤销' },
  },
  batch: {
    normal: { color: 'green', label: '正常' },
    low: { color: 'orange', label: '低库存' },
    depleted: { color: 'default', label: '已用尽' },
    expired: { color: 'red', label: '过期' },
    frozen: { color: 'blue', label: '冻结' },
  },
}

/** 物料使用用途选项与标签。 */
export const USAGE_ROLE_OPTIONS = [
  { label: '起始物料', value: 'starting_material' },
  { label: '试剂', value: 'reagent' },
  { label: '溶剂', value: 'solvent' },
  { label: '催化剂', value: 'catalyst' },
  { label: '标准品', value: 'standard' },
  { label: '耗材', value: 'consumable' },
]

export const usageRoleLabel: Record<string, string> = Object.fromEntries(
  USAGE_ROLE_OPTIONS.map((o) => [o.value, o.label]),
)

/** 物料类别选项与标签。 */
export const CATEGORY_OPTIONS = [
  ...USAGE_ROLE_OPTIONS,
  { label: '中间体', value: 'intermediate' },
  { label: '成品/样品', value: 'product' },
]

export const categoryLabel: Record<string, string> = Object.fromEntries(
  CATEGORY_OPTIONS.map((o) => [o.value, o.label]),
)

export function getStatusMeta(kind: StatusKind, value: string): StatusMeta {
  return MAPS[kind]?.[value] ?? { color: 'default', label: value }
}
