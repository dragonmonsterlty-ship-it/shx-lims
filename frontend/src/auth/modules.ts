import type { SketchIconName } from '../components/sketch'
import type { ModuleKey, User } from '../types'

/** 全部模块键，稳定顺序（门户卡片与管理页多选按此顺序展示）。 */
export const MODULE_KEYS: ModuleKey[] = ['lims', 'refstd']

/** 模块中文名（门户卡片标题、管理页标签、多选项）。 */
export const moduleLabel: Record<ModuleKey, string> = {
  lims: '实验室管理',
  refstd: '对照品管理',
}

/** 模块简介（门户卡片副标题）。 */
export const moduleDescription: Record<ModuleKey, string> = {
  lims: '项目、实验记录、样品检测、试剂库存等合成实验室日常工作。',
  refstd: '对照品台账、领用与消耗流水、效期管理。',
}

/** 每个模块工作区的首页路由（单模块自动重定向、卡片跳转、门户返回目标）。 */
export const moduleHome: Record<ModuleKey, string> = {
  lims: '/dashboard',
  refstd: '/ref-standards',
}

/** 门户卡片角标手账图标（视觉宪法白名单：门户属"看一眼"区域）。 */
export const moduleSketchIcon: Record<ModuleKey, SketchIconName> = {
  lims: 'flask',
  refstd: 'test-tube',
}

/** 模块多选下拉选项。 */
export const MODULE_OPTIONS: { label: string; value: ModuleKey }[] = MODULE_KEYS.map((key) => ({
  label: moduleLabel[key],
  value: key,
}))

const MODULE_KEY_SET = new Set<ModuleKey>(MODULE_KEYS)

function sanitizeModules(modules: ModuleKey[] | null | undefined): ModuleKey[] {
  const valid = (modules ?? []).filter((m): m is ModuleKey => MODULE_KEY_SET.has(m))
  // 去重并按稳定顺序排列，便于展示与比较。
  return MODULE_KEYS.filter((key) => valid.includes(key))
}

/**
 * 用户实际可访问的模块：
 * - `admin` 无视 modules 字段，视为拥有全部模块（与后端约定一致）；
 * - 其余角色取 modules；缺省或非法值兜底为 `["lims"]`，避免把用户挡在门外。
 */
export function effectiveModules(user: Pick<User, 'role' | 'modules'>): ModuleKey[] {
  if (user.role === 'admin') return [...MODULE_KEYS]
  const sanitized = sanitizeModules(user.modules)
  return sanitized.length > 0 ? sanitized : ['lims']
}

/** 是否可访问某工作区模块。 */
export function hasModule(user: Pick<User, 'role' | 'modules'>, module: ModuleKey): boolean {
  return effectiveModules(user).includes(module)
}
