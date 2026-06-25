// 前端 mock 内存数据库。所有 mock 数据集中在此，页面禁止直接引用，
// 一律经由 services 层取数，未来可整体替换为真实 API。

import dayjs from 'dayjs'

import type { Attachment } from '../../types/attachment'
import type { User } from '../../types/auth'
import type { DailyReport, DailyReportActivity } from '../../types/dailyReport'
import type {
  Experiment,
  ExperimentActivity,
  ExperimentMaterialUsage,
} from '../../types/experiment'
import type { InventoryBatch, InventoryTransaction, Material } from '../../types/inventory'
import type { Project, ProjectMember } from '../../types/project'

let seq = 1000
export function nextId(): number {
  seq += 1
  return seq
}

const now = dayjs()
const iso = (d: dayjs.Dayjs) => d.toISOString()
const day = (offset: number) => now.add(offset, 'day').format('YYYY-MM-DD')

function audit(actor = 1) {
  return {
    created_by: actor,
    created_at: iso(now.subtract(20, 'day')),
    updated_by: actor,
    updated_at: iso(now.subtract(1, 'day')),
  }
}

// ---- users（四角色 + 额外操作员） ----
export const users: User[] = [
  { id: 1, username: 'admin', full_name: '系统管理员', email: 'admin@lims.dev', role: 'admin', department: '信息科', is_active: true, must_change_password: false },
  { id: 2, username: 'director', full_name: '王主管', email: 'director@lims.dev', role: 'director', department: '研发中心', is_active: true, must_change_password: false },
  { id: 3, username: 'project_manager', full_name: '张负责人', email: 'project_manager@lims.dev', role: 'project_manager', department: '分析一组', is_active: true, must_change_password: false },
  { id: 4, username: 'op', full_name: '李操作', email: 'op@lims.dev', role: 'operator', department: '分析一组', is_active: true, must_change_password: true },
  { id: 5, username: 'op2', full_name: '赵操作', email: 'op2@lims.dev', role: 'operator', department: '分析二组', is_active: true, must_change_password: false },
]

// ---- projects ----
export const projects: Project[] = [
  { id: 101, project_code: 'PRJ-A', name: '化合物 A 稳定性研究', project_type: '稳定性', lead_user_id: 3, status: 'active', description: 'A 系列化合物长期稳定性考察', start_date: day(-60), end_date: day(120), is_deleted: false, ...audit() },
  { id: 102, project_code: 'PRJ-B', name: '原料药 B 质量研究', project_type: '质量研究', lead_user_id: 2, status: 'active', description: 'B 原料药杂质谱与含量', start_date: day(-30), end_date: day(90), is_deleted: false, ...audit() },
  { id: 103, project_code: 'PRJ-C', name: '中间体 C 工艺验证', project_type: '工艺', lead_user_id: 1, status: 'paused', description: '工艺放大验证', start_date: day(-90), end_date: day(30), is_deleted: false, ...audit() },
  { id: 104, project_code: 'PRJ-D', name: 'D 小试路线开发', project_type: '小试路线', lead_user_id: 3, status: 'completed', description: 'D 化合物小试合成路线', start_date: day(-120), end_date: day(-10), is_deleted: false, ...audit() },
]

// 约定：每个项目的 manager 成员即其负责人（owner，admin/director/project_manager）；
// operator 仅作为 member（项目组员）。下面安排 2-3 个 operator 分布在不同项目。
export const projectMembers: ProjectMember[] = [
  // PRJ-A (owner 张负责人 project_manager=3)
  { id: 201, project_id: 101, user_id: 3, role_in_project: 'manager', ...audit() },
  { id: 202, project_id: 101, user_id: 4, role_in_project: 'member', ...audit() }, // 李操作
  { id: 203, project_id: 101, user_id: 5, role_in_project: 'member', ...audit() }, // 赵操作
  // PRJ-B (owner 王主管 director=2)
  { id: 204, project_id: 102, user_id: 2, role_in_project: 'manager', ...audit() },
  { id: 205, project_id: 102, user_id: 4, role_in_project: 'member', ...audit() }, // 李操作
  // PRJ-C (owner 系统管理员 admin=1)
  { id: 206, project_id: 103, user_id: 1, role_in_project: 'manager', ...audit() },
  { id: 207, project_id: 103, user_id: 5, role_in_project: 'member', ...audit() }, // 赵操作
  // PRJ-D (owner 张负责人 project_manager=3)
  { id: 208, project_id: 104, user_id: 3, role_in_project: 'manager', ...audit() },
  { id: 209, project_id: 104, user_id: 4, role_in_project: 'member', ...audit() }, // 李操作
  { id: 210, project_id: 104, user_id: 5, role_in_project: 'member', ...audit() }, // 赵操作
]

// ---- daily reports（工作日报，复用项目/成员/实验记录）----
// 用户: 1 admin / 2 director / 3 project_manager张 / 4 op李 / 5 op赵
function reviewed(actorId: number, daysAgo: number) {
  return { submitted_at: iso(now.subtract(daysAgo + 1, 'day')), reviewed_by: actorId, reviewed_at: iso(now.subtract(daysAgo, 'day')) }
}
export const dailyReports: DailyReport[] = [
  { id: 8001, user_id: 4, project_id: 101, related_experiment_id: 602, report_date: day(-1), work_content: '完成 A 含量方法学验证的线性考察，6 个浓度点相关系数 0.9998。', issues_risks: '高浓度点峰形略宽，需确认进样体积。', next_plan: '进行重复性与中间精密度。', status: 'submitted', submitted_at: iso(now.subtract(1, 'day')), reviewed_by: null, reviewed_at: null, review_comment: null, is_deleted: false, ...audit(4) },
  { id: 8002, user_id: 4, project_id: 101, related_experiment_id: 601, report_date: day(-2), work_content: 'A-001 强制降解氧化条件取样，HPLC 监测降解杂质。', issues_risks: '无。', next_plan: '汇总降解数据。', status: 'confirmed', review_comment: '记录完整，确认。', is_deleted: false, ...reviewed(3, 1), ...audit(4) },
  { id: 8003, user_id: 5, project_id: 101, related_experiment_id: 603, report_date: day(-1), work_content: 'A 留样观察取样准备，登记留样台账。', issues_risks: '', next_plan: '按月取样。', status: 'draft', submitted_at: null, reviewed_by: null, reviewed_at: null, review_comment: null, is_deleted: false, ...audit(5) },
  { id: 8004, user_id: 5, project_id: 103, related_experiment_id: 606, report_date: day(-1), work_content: 'C 工艺中控取样，监测关键步骤转化率约 92%。', issues_risks: '转化率略低于预期。', next_plan: '优化反应时间。', status: 'submitted', submitted_at: iso(now.subtract(1, 'day')), reviewed_by: null, reviewed_at: null, review_comment: null, is_deleted: false, ...audit(5) },
  { id: 8005, user_id: 4, project_id: 102, related_experiment_id: 604, report_date: day(-2), work_content: 'B 杂质制备半制备分离，收集目标馏分。', issues_risks: '目标峰与相邻峰分离度不足。', next_plan: '调整梯度再分离。', status: 'returned', review_comment: '请补充分离度数据与色谱条件。', is_deleted: false, ...reviewed(2, 1), ...audit(4) },
  { id: 8006, user_id: 4, project_id: 104, related_experiment_id: 608, report_date: day(-3), work_content: 'D 路线 A 小试第三步合成与纯化，收率 45%。', issues_risks: '无。', next_plan: '结构确证。', status: 'confirmed', review_comment: '确认。', is_deleted: false, ...reviewed(3, 2), ...audit(4) },
  { id: 8007, user_id: 3, project_id: 101, related_experiment_id: 602, report_date: day(-1), work_content: '审阅组员方法学数据，安排后续精密度实验分工。', issues_risks: '人力偏紧。', next_plan: '协调仪器排期。', status: 'submitted', submitted_at: iso(now.subtract(1, 'day')), reviewed_by: null, reviewed_at: null, review_comment: null, is_deleted: false, ...audit(3) },
  { id: 8008, user_id: 3, project_id: 104, related_experiment_id: 609, report_date: day(-2), work_content: '规划路线 B 小试方案与物料需求。', issues_risks: '部分起始物料库存不足。', next_plan: '提交采购申请。', status: 'draft', submitted_at: null, reviewed_by: null, reviewed_at: null, review_comment: null, is_deleted: false, ...audit(3) },
  { id: 8009, user_id: 5, project_id: 104, related_experiment_id: 608, report_date: day(-2), work_content: '协助 D 路线 A 小试纯化，柱层析。', issues_risks: '无。', next_plan: '准备 NMR 样品。', status: 'submitted', submitted_at: iso(now.subtract(2, 'day')), reviewed_by: null, reviewed_at: null, review_comment: null, is_deleted: false, ...audit(5) },
  { id: 8010, user_id: 4, project_id: 101, related_experiment_id: null, report_date: day(-4), work_content: '仪器维护：HPLC 更换在线过滤器与密封圈。', issues_risks: '无。', next_plan: '恢复常规检测。', status: 'confirmed', review_comment: '确认。', is_deleted: false, ...reviewed(3, 3), ...audit(4) },
  { id: 8011, user_id: 5, project_id: 103, related_experiment_id: 607, report_date: day(-3), work_content: 'C 杂质归属 LCMS 数据整理（实验后取消，记录留档）。', issues_risks: '样品不足导致实验取消。', next_plan: '等待补样。', status: 'submitted', submitted_at: iso(now.subtract(3, 'day')), reviewed_by: null, reviewed_at: null, review_comment: null, is_deleted: false, ...audit(5) },
  { id: 8012, user_id: 3, project_id: 104, related_experiment_id: null, report_date: day(-3), work_content: '组织 D 项目周进展评审，更新里程碑。', issues_risks: '路线 B 进度待定。', next_plan: '确定路线 B 启动时间。', status: 'confirmed', review_comment: '确认。', is_deleted: false, ...reviewed(1, 2), ...audit(3) },
]

export const dailyReportActivities: DailyReportActivity[] = [
  { id: 8101, report_id: 8002, action: '创建日报', actor_id: 4, at: iso(now.subtract(3, 'day')) },
  { id: 8102, report_id: 8002, action: '提交日报', actor_id: 4, at: iso(now.subtract(2, 'day')) },
  { id: 8103, report_id: 8002, action: '确认日报', actor_id: 3, at: iso(now.subtract(1, 'day')) },
  { id: 8104, report_id: 8005, action: '创建日报', actor_id: 4, at: iso(now.subtract(3, 'day')) },
  { id: 8105, report_id: 8005, action: '提交日报', actor_id: 4, at: iso(now.subtract(2, 'day')) },
  { id: 8106, report_id: 8005, action: '退回日报：请补充分离度数据', actor_id: 2, at: iso(now.subtract(1, 'day')) },
]

// ---- experiments（实验记录，复用 T0.7 项目/用户/成员关系）----
// 项目: 101(project_manager=3; 成员 4,5) 102(director=2; 成员 4) 103(admin=1; 成员 5) 104(project_manager=3; 成员 4,5)
export const experiments: Experiment[] = [
  { id: 601, project_id: 101, experiment_no: 'EXP-A-001', title: 'A-001 强制降解试验', lead_user_id: 4, participant_ids: [5], status: 'reviewed', plan_start_date: day(-20), plan_end_date: day(-10), objective: '考察 A-001 在酸碱氧化条件下的稳定性。', steps: '1. 配制酸/碱/氧化体系；\n2. 分别放置取样；\n3. HPLC 监测降解产物。', result_summary: '氧化条件下产生主要降解杂质，含量下降约 3%。', is_deleted: false, ...audit(4) },
  { id: 602, project_id: 101, experiment_no: 'EXP-A-002', title: 'A 含量方法学验证', lead_user_id: 3, participant_ids: [4, 5], status: 'in_progress', plan_start_date: day(-5), plan_end_date: day(5), objective: '验证 HPLC 含量测定方法的专属性、线性、精密度。', steps: '1. 专属性；\n2. 线性与范围；\n3. 重复性与中间精密度。', result_summary: '', is_deleted: false, ...audit(3) },
  { id: 603, project_id: 101, experiment_no: 'EXP-A-003', title: 'A 留样观察', lead_user_id: 5, participant_ids: [4], status: 'draft', plan_start_date: day(2), plan_end_date: day(12), objective: '长期留样外观与含量观察。', steps: '按月取样检测。', result_summary: '', is_deleted: false, ...audit(3) },
  { id: 604, project_id: 102, experiment_no: 'EXP-B-001', title: 'B 杂质制备', lead_user_id: 4, participant_ids: [], status: 'draft', plan_start_date: day(1), plan_end_date: day(8), objective: '制备未知杂质对照品。', steps: '半制备色谱分离富集。', result_summary: '', is_deleted: false, ...audit(4) },
  { id: 605, project_id: 102, experiment_no: 'EXP-B-002', title: 'B 含量复核', lead_user_id: 4, participant_ids: [], status: 'reviewed', plan_start_date: day(-15), plan_end_date: day(-8), objective: '复核 B 原料药含量。', steps: '平行双样测定。', result_summary: '两份结果一致，含量 99.8%。', is_deleted: false, ...audit(2) },
  { id: 606, project_id: 103, experiment_no: 'EXP-C-001', title: 'C 工艺中控', lead_user_id: 5, participant_ids: [], status: 'in_progress', plan_start_date: day(-3), plan_end_date: day(7), objective: '工艺放大过程中控监测。', steps: '关键步骤取样 HPLC 监测转化率。', result_summary: '', is_deleted: false, ...audit(1) },
  { id: 607, project_id: 103, experiment_no: 'EXP-C-002', title: 'C 杂质归属', lead_user_id: 5, participant_ids: [], status: 'archived', plan_start_date: day(-25), plan_end_date: day(-18), objective: '未知杂质结构归属。', steps: 'LCMS 分析。', result_summary: '因样品不足取消。', is_deleted: false, ...audit(1) },
  { id: 608, project_id: 104, experiment_no: 'EXP-D-001', title: 'D 路线 A 小试', lead_user_id: 3, participant_ids: [4, 5], status: 'reviewed', plan_start_date: day(-40), plan_end_date: day(-20), objective: '验证小试合成路线 A 的可行性。', steps: '三步法合成并纯化。', result_summary: '路线可行，总收率 42%。', is_deleted: false, ...audit(3) },
  { id: 609, project_id: 104, experiment_no: 'EXP-D-002', title: 'D 路线 B 小试', lead_user_id: 4, participant_ids: [5], status: 'draft', plan_start_date: day(3), plan_end_date: day(15), objective: '探索替代路线 B。', steps: '待定。', result_summary: '', is_deleted: false, ...audit(4) },
]

export const experimentActivities: ExperimentActivity[] = [
  { id: 621, experiment_id: 601, action: '创建实验记录', actor_id: 4, at: iso(now.subtract(22, 'day')) },
  { id: 622, experiment_id: 601, action: '状态变更：进行中', actor_id: 4, at: iso(now.subtract(18, 'day')) },
  { id: 623, experiment_id: 601, action: '物料出库', actor_id: 3, at: iso(now.subtract(17, 'day')) },
  { id: 624, experiment_id: 601, action: '状态变更：已完成', actor_id: 4, at: iso(now.subtract(10, 'day')) },
  { id: 625, experiment_id: 602, action: '创建实验记录', actor_id: 3, at: iso(now.subtract(6, 'day')) },
  { id: 626, experiment_id: 602, action: '状态变更：进行中', actor_id: 3, at: iso(now.subtract(4, 'day')) },
]

// ---- 物料主数据（T0.10 库存）----
export const materials: Material[] = [
  { id: 7101, material_code: 'M-SM-001', name: '化合物 A 起始料', category: 'starting_material', cas_no: '50-00-0', specification: '≥98%', unit: 'g', safety_level: '一般', storage_condition: '常温干燥', is_deleted: false, ...audit() },
  { id: 7102, material_code: 'M-INT-001', name: '中间体 C', category: 'intermediate', cas_no: null, specification: '自制', unit: 'g', safety_level: '一般', storage_condition: '2-8℃', is_deleted: false, ...audit() },
  { id: 7103, material_code: 'M-RG-001', name: '三乙胺', category: 'reagent', cas_no: '121-44-8', specification: 'AR', unit: 'mL', safety_level: '易燃', storage_condition: '常温避光', is_deleted: false, ...audit() },
  { id: 7104, material_code: 'M-RG-002', name: '碳酸钾', category: 'reagent', cas_no: '584-08-7', specification: 'AR', unit: 'g', safety_level: '一般', storage_condition: '常温干燥', is_deleted: false, ...audit() },
  { id: 7105, material_code: 'M-SOL-001', name: '二氯甲烷', category: 'solvent', cas_no: '75-09-2', specification: 'HPLC', unit: 'mL', safety_level: '易挥发', storage_condition: '常温避光', is_deleted: false, ...audit() },
  { id: 7106, material_code: 'M-SOL-002', name: '乙酸乙酯', category: 'solvent', cas_no: '141-78-6', specification: 'AR', unit: 'mL', safety_level: '易燃', storage_condition: '常温避光', is_deleted: false, ...audit() },
  { id: 7107, material_code: 'M-CAT-001', name: '钯碳 Pd/C', category: 'catalyst', cas_no: '7440-05-3', specification: '10% Pd', unit: 'g', safety_level: '管制', storage_condition: '2-8℃ 惰性气体', is_deleted: false, ...audit() },
  { id: 7108, material_code: 'M-CON-001', name: '0.22μm 滤膜', category: 'consumable', cas_no: null, specification: 'PTFE', unit: '个', safety_level: '一般', storage_condition: '常温', is_deleted: false, ...audit() },
  { id: 7109, material_code: 'M-STD-001', name: 'A 含量标准品', category: 'standard', cas_no: null, specification: '99.5%', unit: 'mg', safety_level: '一般', storage_condition: '-20℃', is_deleted: false, ...audit() },
  { id: 7110, material_code: 'M-PRD-001', name: 'A 成品样', category: 'product', cas_no: null, specification: '批样', unit: 'g', safety_level: '一般', storage_condition: '2-8℃', is_deleted: false, ...audit() },
]

// ---- 库存批次（15 条，覆盖各状态）----
export const inventoryBatches: InventoryBatch[] = [
  { id: 7201, material_id: 7101, batch_no: 'SM-A-2406', supplier: 'Sigma', purity: '98%', location: '溶剂柜 A1', quantity: 120, unit: 'g', received_date: day(-30), expiry_date: day(300), status: 'normal', remark: '' },
  { id: 7202, material_id: 7101, batch_no: 'SM-A-2405', supplier: 'Sigma', purity: '98%', location: '溶剂柜 A1', quantity: 15, unit: 'g', received_date: day(-90), expiry_date: day(120), status: 'low', remark: '低库存' },
  { id: 7203, material_id: 7102, batch_no: 'INT-C-2405', supplier: '自制', purity: '95%', location: '冰箱 B2', quantity: 60, unit: 'g', received_date: day(-40), expiry_date: day(60), status: 'normal', remark: '' },
  { id: 7204, material_id: 7103, batch_no: 'TEA-2403', supplier: '国药', purity: 'AR', location: '试剂架 C1', quantity: 500, unit: 'mL', received_date: day(-60), expiry_date: day(400), status: 'normal', remark: '' },
  { id: 7205, material_id: 7104, batch_no: 'K2CO3-2402', supplier: '国药', purity: 'AR', location: '试剂架 C2', quantity: 800, unit: 'g', received_date: day(-80), expiry_date: day(500), status: 'normal', remark: '' },
  { id: 7206, material_id: 7105, batch_no: 'DCM-2406', supplier: 'Merck', purity: 'HPLC', location: '溶剂柜 A2', quantity: 4000, unit: 'mL', received_date: day(-20), expiry_date: day(260), status: 'normal', remark: '' },
  { id: 7207, material_id: 7105, batch_no: 'DCM-2405', supplier: 'Merck', purity: 'HPLC', location: '溶剂柜 A2', quantity: 0, unit: 'mL', received_date: day(-120), expiry_date: day(60), status: 'depleted', remark: '已用尽' },
  { id: 7208, material_id: 7106, batch_no: 'EA-2406', supplier: 'Fisher', purity: 'AR', location: '溶剂柜 A3', quantity: 3000, unit: 'mL', received_date: day(-25), expiry_date: day(240), status: 'normal', remark: '' },
  { id: 7209, material_id: 7107, batch_no: 'PdC-2401', supplier: 'Sigma', purity: '10%Pd', location: '管制柜 D1', quantity: 5, unit: 'g', received_date: day(-100), expiry_date: day(200), status: 'low', remark: '管制品低库存' },
  { id: 7210, material_id: 7107, batch_no: 'PdC-2312', supplier: 'Sigma', purity: '10%Pd', location: '管制柜 D1', quantity: 0, unit: 'g', received_date: day(-200), expiry_date: day(-10), status: 'depleted', remark: '' },
  { id: 7211, material_id: 7108, batch_no: 'FLT-2405', supplier: 'Pall', purity: 'PTFE', location: '耗材柜 E1', quantity: 200, unit: '个', received_date: day(-50), expiry_date: null, status: 'normal', remark: '' },
  { id: 7212, material_id: 7109, batch_no: 'STD-A-2404', supplier: '自制', purity: '99.5%', location: '冰箱 -20 F1', quantity: 50, unit: 'mg', received_date: day(-40), expiry_date: day(180), status: 'normal', remark: '' },
  { id: 7213, material_id: 7109, batch_no: 'STD-A-2310', supplier: '自制', purity: '99.0%', location: '冰箱 -20 F1', quantity: 10, unit: 'mg', received_date: day(-260), expiry_date: day(-20), status: 'expired', remark: '已过期' },
  { id: 7214, material_id: 7110, batch_no: 'PRD-A-2406', supplier: '自制', purity: '批样', location: '冰箱 B3', quantity: 30, unit: 'g', received_date: day(-15), expiry_date: day(150), status: 'frozen', remark: '留样冻结' },
  { id: 7215, material_id: 7103, batch_no: 'TEA-2310', supplier: '国药', purity: 'AR', location: '试剂架 C1', quantity: 120, unit: 'mL', received_date: day(-280), expiry_date: day(-30), status: 'expired', remark: '已过期待处理' },
]

// ---- 库存流水（20 条）----
export const inventoryTransactions: InventoryTransaction[] = [
  { id: 7301, material_id: 7101, batch_id: 7201, transaction_type: 'inbound', qty_delta: 150, unit: 'g', source_type: 'manual', source_id: null, actor_id: 1, at: iso(now.subtract(30, 'day')), reason: '采购入库 PO-2406' },
  { id: 7302, material_id: 7101, batch_id: 7201, transaction_type: 'outbound', qty_delta: -30, unit: 'g', source_type: 'manual', source_id: null, actor_id: 4, at: iso(now.subtract(25, 'day')), reason: '领用' },
  { id: 7303, material_id: 7101, batch_id: 7202, transaction_type: 'inbound', qty_delta: 50, unit: 'g', source_type: 'manual', source_id: null, actor_id: 1, at: iso(now.subtract(90, 'day')), reason: '采购入库' },
  { id: 7304, material_id: 7101, batch_id: 7202, transaction_type: 'outbound', qty_delta: -35, unit: 'g', source_type: 'experiment', source_id: 608, actor_id: 3, at: iso(now.subtract(20, 'day')), reason: 'EXP-D-001 出库' },
  { id: 7305, material_id: 7102, batch_id: 7203, transaction_type: 'inbound', qty_delta: 60, unit: 'g', source_type: 'manual', source_id: null, actor_id: 1, at: iso(now.subtract(40, 'day')), reason: '自制入库' },
  { id: 7306, material_id: 7103, batch_id: 7204, transaction_type: 'inbound', qty_delta: 500, unit: 'mL', source_type: 'manual', source_id: null, actor_id: 1, at: iso(now.subtract(60, 'day')), reason: '采购入库' },
  { id: 7307, material_id: 7104, batch_id: 7205, transaction_type: 'inbound', qty_delta: 1000, unit: 'g', source_type: 'manual', source_id: null, actor_id: 1, at: iso(now.subtract(80, 'day')), reason: '采购入库' },
  { id: 7308, material_id: 7104, batch_id: 7205, transaction_type: 'outbound', qty_delta: -200, unit: 'g', source_type: 'manual', source_id: null, actor_id: 5, at: iso(now.subtract(30, 'day')), reason: '领用' },
  { id: 7309, material_id: 7105, batch_id: 7206, transaction_type: 'inbound', qty_delta: 4500, unit: 'mL', source_type: 'manual', source_id: null, actor_id: 1, at: iso(now.subtract(20, 'day')), reason: '采购入库' },
  { id: 7310, material_id: 7105, batch_id: 7206, transaction_type: 'outbound', qty_delta: -100, unit: 'mL', source_type: 'experiment', source_id: 601, actor_id: 3, at: iso(now.subtract(17, 'day')), reason: 'EXP-A-001 出库' },
  { id: 7311, material_id: 7105, batch_id: 7206, transaction_type: 'outbound', qty_delta: -400, unit: 'mL', source_type: 'manual', source_id: null, actor_id: 4, at: iso(now.subtract(10, 'day')), reason: '流动相配制' },
  { id: 7312, material_id: 7105, batch_id: 7207, transaction_type: 'adjustment', qty_delta: -50, unit: 'mL', source_type: 'manual', source_id: null, actor_id: 1, at: iso(now.subtract(15, 'day')), reason: '盘点损耗' },
  { id: 7313, material_id: 7106, batch_id: 7208, transaction_type: 'inbound', qty_delta: 3000, unit: 'mL', source_type: 'manual', source_id: null, actor_id: 1, at: iso(now.subtract(25, 'day')), reason: '采购入库' },
  { id: 7314, material_id: 7107, batch_id: 7209, transaction_type: 'inbound', qty_delta: 10, unit: 'g', source_type: 'manual', source_id: null, actor_id: 1, at: iso(now.subtract(100, 'day')), reason: '采购入库' },
  { id: 7315, material_id: 7107, batch_id: 7209, transaction_type: 'outbound', qty_delta: -5, unit: 'g', source_type: 'experiment', source_id: 606, actor_id: 1, at: iso(now.subtract(3, 'day')), reason: 'EXP-C-001 出库' },
  { id: 7316, material_id: 7108, batch_id: 7211, transaction_type: 'inbound', qty_delta: 200, unit: '个', source_type: 'manual', source_id: null, actor_id: 1, at: iso(now.subtract(50, 'day')), reason: '采购入库' },
  { id: 7317, material_id: 7109, batch_id: 7212, transaction_type: 'inbound', qty_delta: 50, unit: 'mg', source_type: 'manual', source_id: null, actor_id: 1, at: iso(now.subtract(40, 'day')), reason: '标准品入库' },
  { id: 7318, material_id: 7110, batch_id: 7214, transaction_type: 'inbound', qty_delta: 30, unit: 'g', source_type: 'manual', source_id: null, actor_id: 1, at: iso(now.subtract(15, 'day')), reason: '留样入库' },
  { id: 7319, material_id: 7103, batch_id: 7215, transaction_type: 'return', qty_delta: 20, unit: 'mL', source_type: 'manual', source_id: null, actor_id: 4, at: iso(now.subtract(12, 'day')), reason: '退库' },
  { id: 7320, material_id: 7101, batch_id: 7201, transaction_type: 'outbound', qty_delta: -48, unit: 'g', source_type: 'experiment', source_id: 601, actor_id: 3, at: iso(now.subtract(17, 'day')), reason: 'EXP-A-001 出库' },
]

// 实验物料使用（持久化快照，batch_id 指向库存批次）。601 已出库；602 待出库（含库存不足行）。
export const experimentMaterialUsages: ExperimentMaterialUsage[] = [
  { id: 7401, experiment_id: 601, material_id: 7101, material_code: 'M-SM-001', material_name: '化合物 A 起始料', batch_id: 7201, batch_no: 'SM-A-2406', usage_role: 'starting_material', planned_qty: 50, actual_qty: 48, unit: 'g', stock_available: 120, stock_status: 'sufficient', outbound_status: 'dispensed', shortage_qty: null, remark: '' },
  { id: 7402, experiment_id: 601, material_id: 7105, material_code: 'M-SOL-001', material_name: '二氯甲烷', batch_id: 7206, batch_no: 'DCM-2406', usage_role: 'solvent', planned_qty: 100, actual_qty: 100, unit: 'mL', stock_available: 4000, stock_status: 'sufficient', outbound_status: 'dispensed', shortage_qty: null, remark: '' },
  { id: 7403, experiment_id: 602, material_id: 7103, material_code: 'M-RG-001', material_name: '三乙胺', batch_id: 7204, batch_no: 'TEA-2403', usage_role: 'reagent', planned_qty: 10, actual_qty: 12, unit: 'mL', stock_available: 500, stock_status: 'sufficient', outbound_status: 'pending', shortage_qty: null, remark: '待出库' },
  { id: 7404, experiment_id: 602, material_id: 7107, material_code: 'M-CAT-001', material_name: '钯碳 Pd/C', batch_id: 7209, batch_no: 'PdC-2401', usage_role: 'catalyst', planned_qty: 8, actual_qty: 8, unit: 'g', stock_available: 5, stock_status: 'insufficient', outbound_status: 'pending', shortage_qty: null, remark: '库存可能不足' },
]

export const attachments: Attachment[] = [
  { id: 1001, entity_type: 'daily_report', entity_id: 8001, file_name: 'A-含量-线性谱图.png', storage_key: 'mock/uuid-1001', file_type: 'image/png', content_type_detected: 'image/png', file_size: 245_000, sha256: null, thumbnail_key: null, upload_status: 'uploaded', preview_status: 'ready', uploaded_by: 4, uploaded_at: iso(now.subtract(1, 'day')) },
  { id: 1002, entity_type: 'daily_report', entity_id: 8004, file_name: 'C-中控-LCMS.pdf', storage_key: 'mock/uuid-1002', file_type: 'application/pdf', content_type_detected: 'application/pdf', file_size: 1_200_000, sha256: null, thumbnail_key: null, upload_status: 'uploaded', preview_status: null, uploaded_by: 5, uploaded_at: iso(now.subtract(1, 'day')) },
  { id: 1003, entity_type: 'experiment', entity_id: 601, file_name: 'A-001-HPLC图谱.png', storage_key: 'mock/uuid-1003', file_type: 'image/png', content_type_detected: 'image/png', file_size: 320_000, sha256: null, thumbnail_key: null, upload_status: 'uploaded', preview_status: 'ready', uploaded_by: 4, uploaded_at: iso(now.subtract(10, 'day')) },
  { id: 1004, entity_type: 'experiment', entity_id: 601, file_name: 'A-001-降解-LCMS报告.pdf', storage_key: 'mock/uuid-1004', file_type: 'application/pdf', content_type_detected: 'application/pdf', file_size: 980_000, sha256: null, thumbnail_key: null, upload_status: 'uploaded', preview_status: null, uploaded_by: 4, uploaded_at: iso(now.subtract(10, 'day')) },
  { id: 1005, entity_type: 'experiment', entity_id: 608, file_name: 'D-路线A-NMR.pdf', storage_key: 'mock/uuid-1005', file_type: 'application/pdf', content_type_detected: 'application/pdf', file_size: 1_500_000, sha256: null, thumbnail_key: null, upload_status: 'uploaded', preview_status: null, uploaded_by: 3, uploaded_at: iso(now.subtract(20, 'day')) },
]
