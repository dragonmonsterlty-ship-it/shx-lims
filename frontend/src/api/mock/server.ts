// Mock 服务器：在内存 db 上实现各资源 handler，返回统一信封 {code,message,data}，
// 模拟网络延迟与基本状态流转。services 层调用这里并 unwrap。

import dayjs from 'dayjs'

import type { Attachment, AttachmentEntity } from '../../types/attachment'
import type { LoginResponse, Role, User } from '../../types/auth'
import type { ApiEnvelope, Id, PageResult } from '../../types/common'
import type {
  DailyReport,
  DailyReportActivity,
  DailyReportInput,
  DailyReportListQuery,
} from '../../types/dailyReport'
import type {
  Experiment,
  ExperimentActivity,
  ExperimentInput,
  ExperimentListQuery,
  ExperimentMaterialUsage,
  MaterialUsageInput,
  UsageStockStatus,
} from '../../types/experiment'
import type {
  AdjustInput,
  InboundInput,
  InventoryBatch,
  InventoryListQuery,
  InventoryRow,
  InventoryTransaction,
  Material,
  NewBatchInput,
} from '../../types/inventory'
import type {
  Project,
  ProjectInput,
  ProjectListQuery,
  ProjectMember,
  ProjectMemberRole,
} from '../../types/project'
import type { Result, ResultReviewQuery, ResultRow } from '../../types/result'
import type { Sample, SampleListQuery, SampleTestRow, TestMethod } from '../../types/sample'
import { paginate } from '../pagination'
import * as db from './db'

const LATENCY = 220

function ok<T>(data: T, message = 'ok'): Promise<ApiEnvelope<T>> {
  return new Promise((resolve) => {
    setTimeout(() => resolve({ code: 0, message, data }), LATENCY)
  })
}

function fail<T>(code: number, message: string): Promise<ApiEnvelope<T>> {
  return new Promise((resolve) => {
    setTimeout(() => resolve({ code, message, data: null as unknown as T }), LATENCY)
  })
}

function match(haystack: (string | null | undefined)[], keyword?: string): boolean {
  if (!keyword) return true
  const k = keyword.trim().toLowerCase()
  if (!k) return true
  return haystack.some((h) => (h ?? '').toLowerCase().includes(k))
}

function userById(id?: Id | null): User | null {
  return db.users.find((u) => u.id === id) ?? null
}

function managedProjectIds(userId: Id): Id[] {
  return db.projectMembers
    .filter((m) => m.user_id === userId && m.role_in_project === 'manager')
    .map((m) => m.project_id)
}

function memberProjectIds(userId: Id): Id[] {
  return db.projectMembers.filter((m) => m.user_id === userId).map((m) => m.project_id)
}

// ---------- auth / users ----------
export const mockServer = {
  auth: {
    login(username: string, password: string): Promise<ApiEnvelope<LoginResponse>> {
      const user = db.users.find((u) => u.username === username && u.is_active)
      if (!user || !password) {
        return fail(401, '用户名或密码错误')
      }
      const token = `mock-${user.role}-${user.id}`
      return ok<LoginResponse>({
        access_token: token,
        refresh_token: `${token}-refresh`,
        token_type: 'bearer',
        user,
        must_change_password: user.must_change_password,
      })
    },
  },

  users: {
    me(userId: Id): Promise<ApiEnvelope<User>> {
      const user = userById(userId)
      return user ? ok(user) : fail(401, '会话已失效，请重新登录')
    },
    list(): Promise<ApiEnvelope<User[]>> {
      return ok(db.users.filter((u) => u.is_active))
    },
  },

  // ---------- projects ----------
  projects: {
    list(query: ProjectListQuery, currentUser: User): Promise<ApiEnvelope<PageResult<Project>>> {
      let rows = db.projects.filter((p) => !p.is_deleted)
      if (currentUser.role === 'operator' || currentUser.role === 'project_manager') {
        const ids = memberProjectIds(currentUser.id)
        rows = rows.filter((p) => ids.includes(p.id))
      }
      if (query.project_code)
        rows = rows.filter((p) => match([p.project_code], query.project_code))
      if (query.name) rows = rows.filter((p) => match([p.name], query.name))
      if (query.project_type) rows = rows.filter((p) => p.project_type === query.project_type)
      if (query.status) rows = rows.filter((p) => p.status === query.status)
      if (query.lead_user_id) rows = rows.filter((p) => p.lead_user_id === query.lead_user_id)
      if (query.keyword)
        rows = rows.filter((p) => match([p.project_code, p.name, p.project_type], query.keyword))
      return ok(paginate(rows, query.page, query.page_size))
    },
    get(id: Id): Promise<ApiEnvelope<Project>> {
      const p = db.projects.find((x) => x.id === id && !x.is_deleted)
      return p ? ok(p) : fail(404, '项目不存在')
    },
    create(input: ProjectInput, actorId: Id): Promise<ApiEnvelope<Project>> {
      if (db.projects.some((p) => p.project_code === input.project_code && !p.is_deleted)) {
        return fail(409, `项目代码 ${input.project_code} 已存在`)
      }
      const project: Project = {
        id: db.nextId(),
        project_code: input.project_code,
        name: input.name,
        project_type: input.project_type ?? null,
        lead_user_id: input.lead_user_id ?? null,
        status: input.status ?? 'active',
        description: input.description ?? null,
        start_date: input.start_date ?? null,
        end_date: input.end_date ?? null,
        is_deleted: false,
        created_by: actorId,
        created_at: dayjs().toISOString(),
      }
      db.projects.push(project)
      syncProjectMembers(project.id, project.lead_user_id ?? null, input.member_ids ?? [], actorId)
      return ok(project)
    },
    update(id: Id, input: Partial<ProjectInput>, actorId: Id): Promise<ApiEnvelope<Project>> {
      const p = db.projects.find((x) => x.id === id && !x.is_deleted)
      if (!p) return fail(404, '项目不存在')
      const { member_ids, ...fields } = input
      Object.assign(p, fields, { updated_by: actorId, updated_at: dayjs().toISOString() })
      syncProjectMembers(p.id, p.lead_user_id ?? null, member_ids, actorId)
      return ok(p)
    },
    remove(id: Id, actorId: Id): Promise<ApiEnvelope<{ deleted: boolean }>> {
      const p = db.projects.find((x) => x.id === id && !x.is_deleted)
      if (!p) return fail(404, '项目不存在')
      p.is_deleted = true
      p.updated_by = actorId
      p.updated_at = dayjs().toISOString()
      return ok({ deleted: true })
    },
    listMembers(projectId: Id): Promise<ApiEnvelope<ProjectMember[]>> {
      const rows = db.projectMembers
        .filter((m) => m.project_id === projectId)
        .map((m) => ({ ...m, user: userById(m.user_id) }))
      return ok(rows)
    },
    addMember(
      projectId: Id,
      userId: Id,
      role: ProjectMemberRole,
      actorId: Id,
    ): Promise<ApiEnvelope<ProjectMember>> {
      if (db.projectMembers.some((m) => m.project_id === projectId && m.user_id === userId)) {
        return fail(409, '该用户已是项目成员')
      }
      const member: ProjectMember = {
        id: db.nextId(),
        project_id: projectId,
        user_id: userId,
        role_in_project: role,
        created_by: actorId,
        created_at: dayjs().toISOString(),
      }
      db.projectMembers.push(member)
      return ok({ ...member, user: userById(userId) })
    },
    removeMember(projectId: Id, userId: Id): Promise<ApiEnvelope<{ deleted: boolean }>> {
      const idx = db.projectMembers.findIndex(
        (m) => m.project_id === projectId && m.user_id === userId,
      )
      if (idx < 0) return fail(404, '成员不存在')
      db.projectMembers.splice(idx, 1)
      return ok({ deleted: true })
    },
    myMemberships(userId: Id): Promise<ApiEnvelope<{ managed: Id[]; member: Id[] }>> {
      return ok({ managed: managedProjectIds(userId), member: memberProjectIds(userId) })
    },
  },

  // ---------- daily reports ----------
  dailyReports: {
    list(
      query: DailyReportListQuery,
      currentUser: User,
    ): Promise<ApiEnvelope<PageResult<DailyReport>>> {
      let rows = visibleReports(
        db.dailyReports.filter((r) => !r.is_deleted),
        currentUser,
      )
      if (query.project_id) rows = rows.filter((r) => r.project_id === query.project_id)
      if (query.user_id) rows = rows.filter((r) => r.user_id === query.user_id)
      if (query.related_experiment_id)
        rows = rows.filter((r) => r.related_experiment_id === query.related_experiment_id)
      if (query.status) rows = rows.filter((r) => r.status === query.status)
      if (query.date_from) rows = rows.filter((r) => r.report_date >= query.date_from!)
      if (query.date_to) rows = rows.filter((r) => r.report_date <= query.date_to!)
      rows = rows.filter((r) => match([r.work_content, r.issues_risks, r.next_plan], query.keyword))
      rows = [...rows].sort((a, b) => (a.report_date < b.report_date ? 1 : -1))
      return ok(paginate(rows, query.page, query.page_size))
    },
    get(id: Id): Promise<ApiEnvelope<DailyReport>> {
      const r = db.dailyReports.find((x) => x.id === id && !x.is_deleted)
      return r ? ok(r) : fail(404, '日报不存在')
    },
    create(input: DailyReportInput, actorId: Id): Promise<ApiEnvelope<DailyReport>> {
      const itemInputs = input.items?.length
        ? input.items
        : [{
            project_id: input.project_id ?? null,
            experiment_record_id: input.related_experiment_id ?? null,
            content: input.work_content ?? '',
            problem_note: input.issues_risks ?? null,
            next_step: input.next_plan ?? null,
            work_type: 'other',
          }]
      const items = itemInputs.map((item, index) => ({
        id: db.nextId(),
        daily_report_id: 0,
        project_id: item.project_id ?? null,
        experiment_record_id: item.experiment_record_id ?? null,
        work_type: item.work_type ?? 'other',
        content: item.content,
        progress_note: item.progress_note ?? null,
        hours_spent: item.hours_spent ?? null,
        problem_note: item.problem_note ?? null,
        next_step: item.next_step ?? null,
        sort_order: item.sort_order ?? index,
      }))
      const first = items[0]
      const report: DailyReport = {
        id: db.nextId(),
        user_id: actorId,
        project_id: first?.project_id ?? null,
        related_experiment_id: first?.experiment_record_id ?? null,
        report_date: input.report_date,
        work_content: input.work_content ?? first?.content ?? '',
        issues_risks: input.issues_risks ?? first?.problem_note ?? null,
        next_plan: input.next_plan ?? first?.next_step ?? null,
        items,
        status: 'draft',
        submitted_at: null,
        reviewed_by: null,
        reviewed_at: null,
        review_comment: null,
        is_deleted: false,
        created_by: actorId,
        created_at: dayjs().toISOString(),
        updated_by: actorId,
        updated_at: dayjs().toISOString(),
      }
      for (const item of items) item.daily_report_id = report.id
      db.dailyReports.push(report)
      addReportActivity(report.id, '创建日报', actorId)
      return ok(report)
    },
    update(id: Id, input: Partial<DailyReportInput>, actorId: Id): Promise<ApiEnvelope<DailyReport>> {
      const r = db.dailyReports.find((x) => x.id === id && !x.is_deleted)
      if (!r) return fail(404, '日报不存在')
      Object.assign(r, input, { updated_by: actorId, updated_at: dayjs().toISOString() })
      if (input.items) {
        r.items = input.items.map((item, index) => ({
          id: db.nextId(),
          daily_report_id: r.id,
          project_id: item.project_id ?? null,
          experiment_record_id: item.experiment_record_id ?? null,
          work_type: item.work_type ?? 'other',
          content: item.content,
          progress_note: item.progress_note ?? null,
          hours_spent: item.hours_spent ?? null,
          problem_note: item.problem_note ?? null,
          next_step: item.next_step ?? null,
          sort_order: item.sort_order ?? index,
        }))
        const first = r.items[0]
        r.project_id = first?.project_id ?? null
        r.related_experiment_id = first?.experiment_record_id ?? null
        r.work_content = first?.content ?? ''
        r.issues_risks = first?.problem_note ?? null
        r.next_plan = first?.next_step ?? null
      }
      addReportActivity(r.id, '编辑日报', actorId)
      return ok(r)
    },
    submit(id: Id, actorId: Id): Promise<ApiEnvelope<DailyReport>> {
      const r = db.dailyReports.find((x) => x.id === id && !x.is_deleted)
      if (!r) return fail(404, '日报不存在')
      r.status = 'submitted'
      r.submitted_at = dayjs().toISOString()
      r.updated_by = actorId
      r.updated_at = dayjs().toISOString()
      addReportActivity(r.id, '提交日报', actorId)
      return ok(r)
    },
    confirm(id: Id, comment: string | undefined, reviewerId: Id): Promise<ApiEnvelope<DailyReport>> {
      const r = db.dailyReports.find((x) => x.id === id && !x.is_deleted)
      if (!r) return fail(404, '日报不存在')
      if (r.user_id === reviewerId) return fail(403, '提交人不能确认自己的日报')
      r.status = 'confirmed'
      r.reviewed_by = reviewerId
      r.reviewed_at = dayjs().toISOString()
      r.review_comment = comment ?? null
      addReportActivity(r.id, '确认日报', reviewerId)
      return ok(r)
    },
    return(id: Id, comment: string, reviewerId: Id): Promise<ApiEnvelope<DailyReport>> {
      if (!comment || !comment.trim()) return fail(422, '退回必须填写退回原因')
      const r = db.dailyReports.find((x) => x.id === id && !x.is_deleted)
      if (!r) return fail(404, '日报不存在')
      if (r.user_id === reviewerId) return fail(403, '提交人不能退回自己的日报')
      r.status = 'returned'
      r.reviewed_by = reviewerId
      r.reviewed_at = dayjs().toISOString()
      r.review_comment = comment
      addReportActivity(r.id, `退回日报：${comment}`, reviewerId)
      return ok(r)
    },
    listActivities(reportId: Id): Promise<ApiEnvelope<DailyReportActivity[]>> {
      const rows = db.dailyReportActivities
        .filter((a) => a.report_id === reportId)
        .sort((a, b) => (a.at < b.at ? 1 : -1))
      return ok(rows)
    },
  },

  // ---------- attachments ----------
  attachments: {
    listByEntity(
      entityType: AttachmentEntity,
      entityId: Id,
    ): Promise<ApiEnvelope<Attachment[]>> {
      return ok(
        db.attachments.filter((a) => a.entity_type === entityType && a.entity_id === entityId),
      )
    },
    upload(
      entityType: AttachmentEntity,
      entityId: Id,
      file: { name: string; size: number; type: string },
      actorId: Id,
    ): Promise<ApiEnvelope<Attachment>> {
      const att: Attachment = {
        id: db.nextId(),
        entity_type: entityType,
        entity_id: entityId,
        file_name: file.name,
        storage_key: `mock/${crypto.randomUUID?.() ?? Date.now()}`,
        file_type: file.type || null,
        content_type_detected: file.type || null,
        file_size: file.size,
        sha256: null,
        thumbnail_key: null,
        upload_status: 'uploaded',
        preview_status: file.type.startsWith('image/') ? 'ready' : null,
        uploaded_by: actorId,
        uploaded_at: dayjs().toISOString(),
      }
      db.attachments.push(att)
      return ok(att)
    },
    remove(id: Id): Promise<ApiEnvelope<{ deleted: boolean }>> {
      const idx = db.attachments.findIndex((a) => a.id === id)
      if (idx < 0) return fail(404, '附件不存在')
      db.attachments.splice(idx, 1)
      return ok({ deleted: true })
    },
  },

  // ---------- experiments ----------
  experiments: {
    list(query: ExperimentListQuery, currentUser: User): Promise<ApiEnvelope<PageResult<Experiment>>> {
      let rows = visibleExperiments(
        db.experiments.filter((e) => !e.is_deleted),
        currentUser,
      )
      if (query.experiment_no) rows = rows.filter((e) => match([e.experiment_no], query.experiment_no))
      if (query.title) rows = rows.filter((e) => match([e.title], query.title))
      if (query.project_id) rows = rows.filter((e) => e.project_id === query.project_id)
      if (query.status) rows = rows.filter((e) => e.status === query.status)
      if (query.lead_user_id) rows = rows.filter((e) => e.lead_user_id === query.lead_user_id)
      if (query.plan_date_from)
        rows = rows.filter((e) => (e.plan_end_date ?? e.plan_start_date ?? '') >= query.plan_date_from!)
      if (query.plan_date_to)
        rows = rows.filter((e) => (e.plan_start_date ?? e.plan_end_date ?? '') <= query.plan_date_to!)
      rows = [...rows].sort((a, b) =>
        (a.updated_at ?? a.created_at ?? '') < (b.updated_at ?? b.created_at ?? '') ? 1 : -1,
      )
      return ok(paginate(rows, query.page, query.page_size))
    },
    get(id: Id): Promise<ApiEnvelope<Experiment>> {
      const e = db.experiments.find((x) => x.id === id && !x.is_deleted)
      return e ? ok(e) : fail(404, '实验记录不存在')
    },
    create(input: ExperimentInput, actorId: Id): Promise<ApiEnvelope<Experiment>> {
      const expNo = input.experiment_no?.trim() || `EXP-${db.nextId()}`
      if (db.experiments.some((x) => !x.is_deleted && x.experiment_no === expNo)) {
        return fail(409, `实验编号 ${expNo} 已存在`)
      }
      const exp: Experiment = {
        id: db.nextId(),
        project_id: input.project_id,
        experiment_no: expNo,
        title: input.title,
        lead_user_id: input.lead_user_id,
        participant_ids: input.participant_ids ?? [],
        status: input.status ?? 'draft',
        plan_start_date: input.plan_start_date ?? null,
        plan_end_date: input.plan_end_date ?? null,
        objective: input.objective ?? null,
        steps: Array.isArray(input.steps) ? input.steps.join('\n') : (input.steps ?? null),
        result_summary: input.result_summary ?? null,
        conclusion: input.conclusion ?? null,
        next_step: input.next_step ?? null,
        risk_note: input.risk_note ?? null,
        is_deleted: false,
        created_by: actorId,
        created_at: dayjs().toISOString(),
        updated_by: actorId,
        updated_at: dayjs().toISOString(),
      }
      db.experiments.push(exp)
      addExperimentActivity(exp.id, '创建实验记录', actorId)
      syncMaterialUsages(exp.id, input.material_usages ?? [])
      return ok(exp)
    },
    update(id: Id, input: Partial<ExperimentInput>, actorId: Id): Promise<ApiEnvelope<Experiment>> {
      const e = db.experiments.find((x) => x.id === id && !x.is_deleted)
      if (!e) return fail(404, '实验记录不存在')
      if (input.experiment_no) {
        const no = input.experiment_no.trim()
        if (no !== e.experiment_no && db.experiments.some((x) => x.id !== e.id && !x.is_deleted && x.experiment_no === no)) {
          return fail(409, `实验编号 ${no} 已存在`)
        }
      }
      const prevStatus = e.status
      const { material_usages, ...fields } = input
      Object.assign(e, fields, { updated_by: actorId, updated_at: dayjs().toISOString() })
      addExperimentActivity(e.id, '编辑实验记录', actorId)
      if (input.status && input.status !== prevStatus) {
        addExperimentActivity(e.id, `状态变更：${EXPERIMENT_STATUS_LABEL[input.status]}`, actorId)
      }
      if (material_usages !== undefined) {
        syncMaterialUsages(e.id, material_usages)
      }
      return ok(e)
    },
    remove(id: Id, actorId: Id): Promise<ApiEnvelope<{ deleted: boolean }>> {
      const e = db.experiments.find((x) => x.id === id && !x.is_deleted)
      if (!e) return fail(404, '实验记录不存在')
      e.is_deleted = true
      e.updated_by = actorId
      e.updated_at = dayjs().toISOString()
      addExperimentActivity(e.id, '删除实验记录', actorId)
      return ok({ deleted: true })
    },
    listActivities(experimentId: Id): Promise<ApiEnvelope<ExperimentActivity[]>> {
      const rows = db.experimentActivities
        .filter((a) => a.experiment_id === experimentId)
        .sort((a, b) => (a.at < b.at ? 1 : -1))
      return ok(rows)
    },
    listMaterialUsages(experimentId: Id): Promise<ApiEnvelope<ExperimentMaterialUsage[]>> {
      return ok(db.experimentMaterialUsages.filter((u) => u.experiment_id === experimentId))
    },
    dispenseMaterials(experimentId: Id, actorId: Id): Promise<ApiEnvelope<ExperimentMaterialUsage[]>> {
      const rows = db.experimentMaterialUsages.filter((u) => u.experiment_id === experimentId)
      let changed = 0
      for (const u of rows) {
        if (u.outbound_status !== 'pending') continue // 已出库不再扣减
        if (u.batch_id == null) continue // 未关联库存，跳过
        const batch = db.inventoryBatches.find((b) => b.id === u.batch_id)
        if (!batch) continue
        const need = u.actual_qty ?? 0
        if (need <= 0) continue
        const deducted = Math.min(need, batch.quantity)
        if (need <= batch.quantity) {
          u.outbound_status = 'dispensed'
          u.shortage_qty = null
          u.stock_status = 'sufficient'
        } else {
          u.shortage_qty = need - batch.quantity
          u.outbound_status = 'insufficient'
          u.stock_status = 'insufficient'
        }
        batch.quantity -= deducted
        applyBatchStatus(batch)
        u.stock_available = batch.quantity
        pushTxn(batch, 'outbound', -deducted, actorId, 'experiment', experimentId, `实验出库 #${experimentId}`)
        changed += 1
      }
      if (changed > 0) addExperimentActivity(experimentId, '物料出库', actorId)
      return ok(rows)
    },
  },

  inventory: {
    listMaterials(): Promise<ApiEnvelope<Material[]>> {
      return ok(db.materials.filter((m) => !m.is_deleted))
    },
    listAllBatches(): Promise<ApiEnvelope<InventoryBatch[]>> {
      return ok(db.inventoryBatches)
    },
    listRows(query: InventoryListQuery): Promise<ApiEnvelope<PageResult<InventoryRow>>> {
      let rows: InventoryRow[] = db.inventoryBatches.map((b) => {
        const m = db.materials.find((x) => x.id === b.material_id)
        return {
          batch_id: b.id,
          material_id: b.material_id,
          material_code: m?.material_code ?? '',
          material_name: m?.name ?? '',
          category: m?.category ?? 'reagent',
          cas_no: m?.cas_no ?? null,
          batch_no: b.batch_no,
          supplier: b.supplier ?? null,
          location: b.location ?? null,
          quantity: b.quantity,
          unit: b.unit,
          expiry_date: b.expiry_date ?? null,
          status: b.status,
        }
      })
      if (query.material_code) rows = rows.filter((r) => match([r.material_code], query.material_code))
      if (query.material_name) rows = rows.filter((r) => match([r.material_name], query.material_name))
      if (query.cas_no) rows = rows.filter((r) => match([r.cas_no], query.cas_no))
      if (query.category) rows = rows.filter((r) => r.category === query.category)
      if (query.batch_no) rows = rows.filter((r) => match([r.batch_no], query.batch_no))
      if (query.supplier) rows = rows.filter((r) => match([r.supplier], query.supplier))
      if (query.location) rows = rows.filter((r) => match([r.location], query.location))
      if (query.status) rows = rows.filter((r) => r.status === query.status)
      return ok(paginate(rows, query.page, query.page_size))
    },
    getBatch(batchId: Id): Promise<ApiEnvelope<{ batch: InventoryBatch; material: Material | null }>> {
      const batch = db.inventoryBatches.find((b) => b.id === batchId)
      if (!batch) return fail(404, '库存批次不存在')
      const material = db.materials.find((m) => m.id === batch.material_id) ?? null
      return ok({ batch, material })
    },
    listTransactions(batchId: Id): Promise<ApiEnvelope<InventoryTransaction[]>> {
      const rows = db.inventoryTransactions
        .filter((t) => t.batch_id === batchId)
        .sort((a, b) => (a.at < b.at ? 1 : -1))
      return ok(rows)
    },
    listBatchExperiments(batchId: Id): Promise<
      ApiEnvelope<
        {
          experiment_id: Id
          experiment_no: string
          title: string
          project_id: Id
          project_code: string
          project_name: string
          actual_qty: number | null
          unit: string | null
          outbound_status: string
        }[]
      >
    > {
      const rows = db.experimentMaterialUsages
        .filter((u) => u.batch_id === batchId)
        .map((u) => {
          const e = db.experiments.find((x) => x.id === u.experiment_id)
          const p = db.projects.find((x) => x.id === e?.project_id)
          return {
            experiment_id: u.experiment_id,
            experiment_no: e?.experiment_no ?? '',
            title: e?.title ?? '',
            project_id: e?.project_id ?? 0,
            project_code: p?.project_code ?? '',
            project_name: p?.name ?? '',
            actual_qty: u.actual_qty ?? null,
            unit: u.unit ?? null,
            outbound_status: u.outbound_status,
          }
        })
      return ok(rows)
    },
    createBatch(input: NewBatchInput, actorId: Id): Promise<ApiEnvelope<InventoryBatch>> {
      let materialId = input.material_id
      if (!materialId) {
        if (!input.material_code || !input.name || !input.category) {
          return fail(422, '新建物料需填写物料编号、名称与类别')
        }
        const material: Material = {
          id: db.nextId(),
          material_code: input.material_code,
          name: input.name,
          category: input.category,
          cas_no: input.cas_no ?? null,
          specification: input.specification ?? null,
          unit: input.unit,
          safety_level: input.safety_level ?? null,
          storage_condition: input.storage_condition ?? null,
          is_deleted: false,
          created_by: actorId,
          created_at: dayjs().toISOString(),
        }
        db.materials.push(material)
        materialId = material.id
      }
      const batch: InventoryBatch = {
        id: db.nextId(),
        material_id: materialId,
        batch_no: input.batch_no,
        supplier: input.supplier ?? null,
        purity: input.purity ?? null,
        location: input.location ?? null,
        quantity: input.quantity,
        unit: input.unit,
        received_date: input.received_date ?? null,
        expiry_date: input.expiry_date ?? null,
        status: input.quantity > 0 ? 'normal' : 'depleted',
        remark: input.remark ?? null,
      }
      db.inventoryBatches.push(batch)
      pushTxn(batch, 'inbound', input.quantity, actorId, 'manual', null, input.remark ?? '新建批次入库')
      return ok(batch)
    },
    inbound(input: InboundInput, actorId: Id): Promise<ApiEnvelope<InventoryBatch>> {
      const batch = db.inventoryBatches.find((b) => b.id === input.batch_id)
      if (!batch) return fail(404, '库存批次不存在')
      if (input.qty <= 0) return fail(422, '入库数量必须大于 0')
      batch.quantity += input.qty
      applyBatchStatus(batch)
      pushTxn(batch, 'inbound', input.qty, actorId, 'manual', null, input.reason ?? '手动入库')
      return ok(batch)
    },
    adjust(input: AdjustInput, actorId: Id): Promise<ApiEnvelope<InventoryBatch>> {
      const batch = db.inventoryBatches.find((b) => b.id === input.batch_id)
      if (!batch) return fail(404, '库存批次不存在')
      if (batch.quantity + input.qty_delta < 0) return fail(422, '调整后库存不能为负')
      batch.quantity += input.qty_delta
      applyBatchStatus(batch)
      pushTxn(batch, 'adjustment', input.qty_delta, actorId, 'manual', null, input.reason ?? '盘点调整')
      return ok(batch)
    },
    setFrozen(batchId: Id, frozen: boolean, actorId: Id): Promise<ApiEnvelope<InventoryBatch>> {
      const batch = db.inventoryBatches.find((b) => b.id === batchId)
      if (!batch) return fail(404, '库存批次不存在')
      batch.status = frozen ? 'frozen' : batch.quantity > 0 ? 'normal' : 'depleted'
      pushTxn(batch, 'adjustment', 0, actorId, 'manual', null, frozen ? '冻结' : '解冻')
      return ok(batch)
    },
  },

  // ---------- samples / methods / results ----------
  samples: {
    list(query: SampleListQuery, currentUser: User): Promise<ApiEnvelope<PageResult<Sample>>> {
      let rows = db.samples.filter((s) => !s.is_deleted)
      if (currentUser.role === 'operator' || currentUser.role === 'project_manager') {
        const ids = memberProjectIds(currentUser.id)
        rows = rows.filter((s) => ids.includes(s.project_id))
      }
      if (query.project_id) rows = rows.filter((s) => s.project_id === query.project_id)
      if (query.status) rows = rows.filter((s) => s.status === query.status)
      if (query.priority) rows = rows.filter((s) => s.priority === query.priority)
      rows = rows.filter((s) => match([s.sample_code, s.name, s.compound_name, s.batch_no], query.keyword))
      return ok(paginate(rows, query.page, query.page_size))
    },
    get(id: Id): Promise<ApiEnvelope<Sample>> {
      const s = db.samples.find((x) => x.id === id && !x.is_deleted)
      return s ? ok(s) : fail(404, '样品不存在')
    },
    tests(sampleId: Id): Promise<ApiEnvelope<SampleTestRow[]>> {
      const rows: SampleTestRow[] = db.sampleTests
        .filter((t) => t.sample_id === sampleId)
        .map((t) => {
          const method = db.testMethods.find((m) => m.id === t.test_method_id)
          const result = db.results.find((r) => r.sample_test_id === t.id)
          return {
            id: t.id,
            sample_id: t.sample_id,
            test_method_id: t.test_method_id,
            method_code: method?.code ?? '',
            method_name: method?.name ?? '',
            unit: method?.unit ?? null,
            spec_lower: method?.spec_lower ?? null,
            spec_upper: method?.spec_upper ?? null,
            spec_text: method?.spec_text ?? null,
            assigned_to: t.assigned_to ?? null,
            status: t.status,
            value_num: result?.value_num ?? null,
            value_text: result?.value_text ?? null,
            judgment: result?.judgment ?? null,
            review_status: result?.review_status ?? null,
            result_id: result?.id ?? null,
          }
        })
      return ok(rows)
    },
  },

  testMethods: {
    list(): Promise<ApiEnvelope<TestMethod[]>> {
      return ok(db.testMethods.filter((m) => m.is_active))
    },
  },

  results: {
    reviewList(query: ResultReviewQuery, currentUser: User): Promise<ApiEnvelope<PageResult<ResultRow>>> {
      const scopedProjects =
        currentUser.role === 'admin' || currentUser.role === 'director'
          ? null
          : managedProjectIds(currentUser.id)
      let rows: ResultRow[] = db.results.map((r) => {
        const test = db.sampleTests.find((t) => t.id === r.sample_test_id)
        const sample = db.samples.find((s) => s.id === test?.sample_id)
        const method = db.testMethods.find((m) => m.id === test?.test_method_id)
        return {
          id: r.id,
          sample_test_id: r.sample_test_id,
          sample_id: sample?.id ?? 0,
          sample_code: sample?.sample_code ?? '',
          project_id: sample?.project_id ?? 0,
          method_name: method?.name ?? '',
          unit: method?.unit ?? null,
          value_num: r.value_num ?? null,
          value_text: r.value_text ?? null,
          judgment: r.judgment ?? null,
          review_status: r.review_status,
          entered_by: r.entered_by ?? null,
          entered_at: r.entered_at ?? null,
        }
      })
      if (scopedProjects) rows = rows.filter((r) => scopedProjects.includes(r.project_id))
      if (query.review_status) rows = rows.filter((r) => r.review_status === query.review_status)
      if (query.project_id) rows = rows.filter((r) => r.project_id === query.project_id)
      rows = rows.filter((r) => match([r.sample_code, r.method_name], query.keyword))
      return ok(paginate(rows, query.page, query.page_size))
    },
    review(id: Id, action: 'approve' | 'reject', comment: string | undefined, reviewerId: Id): Promise<ApiEnvelope<Result>> {
      const r = db.results.find((x) => x.id === id)
      if (!r) return fail(404, '结果不存在')
      if (r.entered_by === reviewerId) return fail(403, '录入人不能审核自己的结果')
      if (action === 'reject' && (!comment || !comment.trim())) {
        return fail(422, '退回必须填写退回原因')
      }
      r.review_status = action === 'approve' ? 'approved' : 'rejected'
      r.reviewed_by = reviewerId
      r.reviewed_at = dayjs().toISOString()
      r.review_comment = comment ?? null
      return ok(r)
    },
  },
}

// ---------- internal helpers ----------
/** 日报可见范围：admin/director 全部；pm 本人 + 负责项目成员；operator 仅本人。 */
function visibleReports(rows: DailyReport[], currentUser: User): DailyReport[] {
  const role: Role = currentUser.role
  if (role === 'admin' || role === 'director') return rows
  if (role === 'operator') return rows.filter((r) => r.user_id === currentUser.id)
  // project_manager
  const managed = new Set(managedProjectIds(currentUser.id))
  return rows.filter(
    (r) => r.user_id === currentUser.id || (r.project_id != null && managed.has(r.project_id)),
  )
}

function addReportActivity(reportId: Id, action: string, actorId: Id): void {
  db.dailyReportActivities.push({
    id: db.nextId(),
    report_id: reportId,
    action,
    actor_id: actorId,
    at: dayjs().toISOString(),
  })
}

const EXPERIMENT_STATUS_LABEL: Record<Experiment['status'], string> = {
  draft: '草稿',
  in_progress: '进行中',
  submitted: '已提交',
  reviewed: '已审核',
  archived: '已归档',
}

/** 实验可见范围（与前端 canViewExperiment 一致）。 */
function visibleExperiments(rows: Experiment[], currentUser: User): Experiment[] {
  if (currentUser.role === 'admin' || currentUser.role === 'director') return rows
  const member = new Set(memberProjectIds(currentUser.id))
  if (currentUser.role === 'project_manager') {
    return rows.filter((e) => member.has(e.project_id))
  }
  // operator：参与项目内、且本人为负责人或参与人
  return rows.filter(
    (e) =>
      member.has(e.project_id) &&
      (e.lead_user_id === currentUser.id || e.participant_ids.includes(currentUser.id)),
  )
}

function addExperimentActivity(experimentId: Id, action: string, actorId: Id): void {
  db.experimentActivities.push({
    id: db.nextId(),
    experiment_id: experimentId,
    action,
    actor_id: actorId,
    at: dayjs().toISOString(),
  })
}

/** 写一条库存流水，并将批次余额对齐到 quantity（quantity 已由调用方更新）。 */
function pushTxn(
  batch: InventoryBatch,
  type: InventoryTransaction['transaction_type'],
  qtyDelta: number,
  actorId: Id,
  sourceType: 'manual' | 'experiment',
  sourceId: Id | null,
  reason: string,
): void {
  db.inventoryTransactions.push({
    id: db.nextId(),
    material_id: batch.material_id,
    batch_id: batch.id,
    transaction_type: type,
    qty_delta: qtyDelta,
    unit: batch.unit,
    source_type: sourceType,
    source_id: sourceId,
    actor_id: actorId,
    at: dayjs().toISOString(),
    reason,
  })
}

/**
 * 余额变化后重算批次状态（冻结/过期保持，售罄置 depleted，恢复置 normal）。
 * 注意：低库存(low) 目前由 mock 的 status 字段直接驱动，未做真实阈值计算。
 * T1.1+ 可为 Material/Batch 增加 low_stock_threshold，并据 quantity 动态判定 low。
 */
function applyBatchStatus(batch: InventoryBatch): void {
  if (batch.status === 'frozen') return
  if (batch.quantity <= 0) {
    batch.status = 'depleted'
  } else if (batch.status === 'depleted') {
    batch.status = 'normal'
  }
}

/** 由库存批次推导物料使用快照（用量校验：实际 > 库存 标记不足）。 */
function buildUsageSnapshot(
  experimentId: Id,
  input: MaterialUsageInput,
  id: Id,
): ExperimentMaterialUsage {
  const batch =
    input.batch_id != null
      ? db.inventoryBatches.find((b) => b.id === input.batch_id)
      : undefined
  const material = batch ? db.materials.find((m) => m.id === batch.material_id) : undefined
  const actual = input.actual_qty ?? null
  let stockStatus: UsageStockStatus
  if (!batch) stockStatus = 'no_stock_link'
  else if ((actual ?? 0) > batch.quantity) stockStatus = 'insufficient'
  else stockStatus = 'sufficient'
  return {
    id,
    experiment_id: experimentId,
    material_id: material?.id ?? null,
    material_code: material?.material_code ?? '',
    material_name: material?.name ?? '',
    batch_id: input.batch_id ?? null,
    batch_no: batch?.batch_no ?? null,
    usage_role: input.usage_role,
    planned_qty: input.planned_qty ?? null,
    actual_qty: actual,
    unit: batch?.unit ?? material?.unit ?? null,
    stock_available: batch ? batch.quantity : null,
    stock_status: stockStatus,
    outbound_status: 'pending',
    shortage_qty: null,
    remark: input.remark ?? null,
  }
}

/**
 * 同步实验物料使用：保留已出库（非 pending）行，pending 行用提交集合替换。
 * 普通保存不扣库存；出库仅由 dispenseMaterials 触发。
 */
function syncMaterialUsages(experimentId: Id, rows: MaterialUsageInput[]): void {
  const kept = db.experimentMaterialUsages.filter(
    (u) => u.experiment_id === experimentId && u.outbound_status !== 'pending',
  )
  const keptIds = new Set(kept.map((u) => u.id))
  for (let i = db.experimentMaterialUsages.length - 1; i >= 0; i--) {
    if (db.experimentMaterialUsages[i].experiment_id === experimentId) {
      db.experimentMaterialUsages.splice(i, 1)
    }
  }
  db.experimentMaterialUsages.push(...kept)
  for (const row of rows) {
    if (row.id != null && keptIds.has(row.id)) continue // 已出库行保持不变
    db.experimentMaterialUsages.push(buildUsageSnapshot(experimentId, row, db.nextId()))
  }
}

/**
 * 同步项目成员：manager 始终等于负责人 owner；member 为传入的组员集合。
 * memberIds 为 undefined 时只同步 manager，不动组员（用于未改成员的更新）。
 */
function syncProjectMembers(
  projectId: Id,
  ownerId: Id | null,
  memberIds: Id[] | undefined,
  actorId: Id,
): void {
  const ts = dayjs().toISOString()
  if (ownerId != null) {
    for (let i = db.projectMembers.length - 1; i >= 0; i--) {
      const m = db.projectMembers[i]
      // 移除非 owner 的 manager 行，以及 owner 残留的 member 行
      if (m.project_id === projectId && m.role_in_project === 'manager' && m.user_id !== ownerId) {
        db.projectMembers.splice(i, 1)
      } else if (m.project_id === projectId && m.user_id === ownerId && m.role_in_project === 'member') {
        db.projectMembers.splice(i, 1)
      }
    }
    const hasOwner = db.projectMembers.some(
      (m) => m.project_id === projectId && m.user_id === ownerId && m.role_in_project === 'manager',
    )
    if (!hasOwner) {
      db.projectMembers.push({
        id: db.nextId(),
        project_id: projectId,
        user_id: ownerId,
        role_in_project: 'manager',
        created_by: actorId,
        created_at: ts,
      })
    }
  }
  if (memberIds !== undefined) {
    const wanted = new Set(memberIds.filter((uid) => uid !== ownerId))
    for (let i = db.projectMembers.length - 1; i >= 0; i--) {
      const m = db.projectMembers[i]
      if (m.project_id === projectId && m.role_in_project === 'member' && !wanted.has(m.user_id)) {
        db.projectMembers.splice(i, 1)
      }
    }
    for (const uid of wanted) {
      const exists = db.projectMembers.some(
        (m) => m.project_id === projectId && m.user_id === uid,
      )
      if (!exists) {
        db.projectMembers.push({
          id: db.nextId(),
          project_id: projectId,
          user_id: uid,
          role_in_project: 'member',
          created_by: actorId,
          created_at: ts,
        })
      }
    }
  }
}
