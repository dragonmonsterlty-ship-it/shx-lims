import type { AttachmentEntity, DailyReport, Experiment, Id, Project, Role, User } from '../types'
import type { ResultStatus, TaskStatus } from '../types'

/** 角色中文标签（operator 显示为「操作员」，值仍为 operator）。 */
export const roleLabel: Record<Role, string> = {
  admin: '系统管理员',
  director: '主管',
  project_manager: '项目负责人',
  researcher: '研究员',
  operator: '操作员',
  viewer: '只读用户',
}

/** 与后端 PROJECT_OWNER_ROLES 保持一致。 */
export const OWNER_ROLES: Role[] = ['admin', 'project_manager']

export function isOwnerRole(role: Role): boolean {
  return OWNER_ROLES.includes(role)
}

/** director 在日报/结果等模块只读；项目模块按本文件细则单独判定。 */
export function isReadOnly(role: Role): boolean {
  return role === 'director' || role === 'viewer'
}

/**
 * 前端按钮/菜单显隐用的能力判断。范围权限（本项目）以后端行级过滤为准，
 * 这里只做角色显隐 + 负责人归属判断，不作为业务真相；提交时仍二次校验。
 */
export const can = {
  manageUsers: (role: Role) => canManageUsers(role),
  viewAdmin: (role: Role) => canUseAdminRoute(role),
  /** 新建项目：admin / director / project_manager 可见。 */
  createProject: (role: Role) => role === 'admin' || role === 'project_manager',
  review: (role: Role) => role !== 'operator' && role !== 'viewer',
  writeData: (role: Role) => !isReadOnly(role),
}

export function canManageUsers(role: Role): boolean {
  return role === 'admin'
}

export function canUseAdminRoute(role: Role): boolean {
  return role === 'admin'
}

export function canViewAuditLogs(role: Role): boolean {
  return role === 'admin' || role === 'project_manager'
}

export function canViewUserAuditTimeline(
  user: Pick<User, 'id' | 'role'>,
  targetUserId: Id,
): boolean {
  return user.role === 'admin' || user.id === targetUserId
}

/**
 * 是否可编辑某项目基础信息：
 * - admin：全部项目；
 * - project_manager：仅自己负责（lead_user_id === 本人）的项目；
 * - operator：不可。
 */
export function canEditProject(user: User, project: Pick<Project, 'lead_user_id'>): boolean {
  if (user.role === 'admin') return true
  if (user.role === 'project_manager') return project.lead_user_id === user.id
  return false
}

/** 是否可管理项目成员：与编辑项目同口径。 */
export function canManageMembers(user: User, project: Pick<Project, 'lead_user_id'>): boolean {
  return canEditProject(user, project)
}

// ---------- 实验记录权限 ----------

/** 当前用户的项目归属集合：managed=负责的项目，member=参与（含负责）的项目。 */
export interface ProjectScope {
  managed: Set<Id>
  member: Set<Id>
}

type ExperimentLike = Pick<
  Experiment,
  'project_id' | 'lead_user_id' | 'participant_ids' | 'created_by'
>

/** 可新建实验记录：所有已登录角色（具体项目范围由表单限制为可见项目）。 */
export function canCreateExperiment(role: Role): boolean {
  return ['admin', 'project_manager', 'operator'].includes(role)
}

export function canViewExperiment(user: User, exp: ExperimentLike, scope: ProjectScope): boolean {
  if (user.role === 'admin') return true
  if (user.role === 'project_manager') return scope.managed.has(exp.project_id)
  return (
    scope.member.has(exp.project_id) &&
    (exp.lead_user_id === user.id || exp.participant_ids.includes(user.id))
  )
}

/**
 * 可编辑实验记录：
 * - admin：全部；
 * - project_manager：自己负责项目下的实验，或自己为实验负责人/参与人的实验；
 * - operator：自己创建或自己为负责人的实验。
 */
export function canEditExperiment(user: User, exp: ExperimentLike, scope: ProjectScope): boolean {
  if (user.role === 'admin' || user.role === 'director') return true
  if (user.role === 'project_manager') {
    return (
      scope.managed.has(exp.project_id) ||
      exp.lead_user_id === user.id ||
      exp.participant_ids.includes(user.id)
    )
  }
  return exp.created_by === user.id || exp.lead_user_id === user.id
}

/** 可删除实验记录：仅 admin。 */
export function canDeleteExperiment(role: Role): boolean {
  return role === 'admin'
}

/**
 * 可确认物料出库：
 * - admin：全部；
 * - project_manager：自己负责项目下的实验；
 * - operator：不可。
 */
export function canDispenseMaterials(
  user: User,
  exp: Pick<Experiment, 'project_id'>,
  scope: ProjectScope,
): boolean {
  if (user.role === 'admin' || user.role === 'director') return true
  if (user.role === 'project_manager') {
    return scope.managed.has(exp.project_id)
  }
  return false
}

// ---------- 库存权限 ----------

/** 手动入库/调整/冻结/新增批次：admin / director。 */
export function canManageInventory(role: Role): boolean {
  return role === 'admin' || role === 'director'
}

/** 批量导入库存：admin / director / project_manager / operator。 */
export function canImportInventory(role: Role): boolean {
  return (
    role === 'admin' ||
    role === 'director' ||
    role === 'project_manager' ||
    role === 'operator'
  )
}

// ---------- 样品 / 检测 / 结果权限 ----------

export function canManageSample(
  user: Pick<User, 'id' | 'role'>,
  projectId: Id,
  scope: ProjectScope,
): boolean {
  if (user.role === 'admin') return true
  return user.role === 'project_manager' && scope.managed.has(projectId)
}

export function canExecuteTestTask(
  user: Pick<User, 'id' | 'role'>,
  task: { assigned_to?: Id | null; status: TaskStatus | string },
): boolean {
  return (
    user.role === 'operator' &&
    task.assigned_to === user.id &&
    ['pending', 'in_progress'].includes(task.status)
  )
}

export function canReviewTestResult(
  user: Pick<User, 'id' | 'role'>,
  projectId: Id,
  resultStatus: ResultStatus,
  scope: ProjectScope,
): boolean {
  if (resultStatus !== 'submitted') return false
  if (user.role === 'admin') return true
  return user.role === 'project_manager' && scope.managed.has(projectId)
}

// ---------- 附件权限（T1.6A） ----------

export interface AttachmentObjectContext {
  entityType: AttachmentEntity
  projectId: Id
  editable: boolean
  ownerId?: Id | null
  assignedTo?: Id | null
}

export interface AttachmentLike {
  uploaded_by?: Id | null
}

export function canUploadAttachment(
  user: Pick<User, 'id' | 'role'>,
  context: AttachmentObjectContext,
  scope: ProjectScope,
): boolean {
  if (!context.editable) return false
  if (isReadOnly(user.role)) return false
  if (user.role === 'admin') return true
  if (user.role === 'project_manager') return scope.managed.has(context.projectId)
  if (context.assignedTo != null) return context.assignedTo === user.id
  if (context.ownerId != null) return context.ownerId === user.id
  return scope.member.has(context.projectId)
}

export function canDeleteAttachment(
  user: Pick<User, 'id' | 'role'>,
  attachment: AttachmentLike,
  context: AttachmentObjectContext,
  scope: ProjectScope,
): boolean {
  if (user.role === 'operator' && attachment.uploaded_by !== user.id) return false
  return canUploadAttachment(user, context, scope)
}

// ---------- 日报权限 ----------

type ReportLike = Pick<DailyReport, 'user_id' | 'project_id' | 'status'>

export function canCreateReport(role: Role): boolean {
  return !isReadOnly(role)
}

export function canViewReport(user: User, r: ReportLike, scope: ProjectScope): boolean {
  if (user.role === 'admin' || user.role === 'director') return true
  if (r.user_id === user.id) return true
  if (user.role === 'project_manager' && r.project_id != null) {
    return scope.managed.has(r.project_id)
  }
  return false
}

/** 仅本人、且状态为草稿或已退回时可编辑/提交。 */
export function canEditReport(user: User, r: ReportLike): boolean {
  return (
    !isReadOnly(user.role) &&
    r.user_id === user.id &&
    (r.status === 'draft' || r.status === 'returned')
  )
}

/**
 * 可确认/退回日报：状态为已提交、非本人、且 admin/director 或 project_manager 负责该项目。
 */
export function canConfirmReport(user: User, r: ReportLike, scope: ProjectScope): boolean {
  if (r.status !== 'submitted' || r.user_id === user.id) return false
  if (user.role === 'admin' || user.role === 'director') return true
  if (user.role === 'project_manager' && r.project_id != null) {
    return scope.managed.has(r.project_id)
  }
  return false
}
