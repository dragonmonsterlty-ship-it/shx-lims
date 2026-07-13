const configuredBaseUrl =
  process.env.VITE_API_BASE_URL || 'http://127.0.0.1:18000/api'
const baseUrl = configuredBaseUrl.replace(/\/+$/, '')
const username = process.env.LIMS_VERIFY_USERNAME || 'admin'
const password = process.env.LIMS_VERIFY_PASSWORD || 'password123'

async function api(path, { token, method = 'GET', body } = {}) {
  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers: {
      Accept: 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(body ? { 'Content-Type': 'application/json' } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  const envelope = await response.json()
  if (!response.ok || envelope.code !== 0) {
    throw new Error(
      `${method} ${path} failed: HTTP ${response.status}, code=${envelope.code}, message=${envelope.message}`,
    )
  }
  return envelope.data
}

async function loginAs(username) {
  return api('/auth/login', {
    method: 'POST',
    body: { username, password },
  })
}

async function expectHttp(path, expectedStatus, { token, method = 'GET', body } = {}) {
  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers: {
      Accept: 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(body ? { 'Content-Type': 'application/json' } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (response.status !== expectedStatus) {
    throw new Error(`${method} ${path}: expected HTTP ${expectedStatus}, got ${response.status}`)
  }
}

function assertPage(name, value) {
  if (
    !value ||
    !Array.isArray(value.items) ||
    typeof value.total !== 'number' ||
    typeof value.page !== 'number' ||
    typeof value.page_size !== 'number'
  ) {
    throw new Error(`${name} does not match items/total/page/page_size`)
  }
}

function assertTimeline(name, value, entityType, entityId) {
  if (!Array.isArray(value)) {
    throw new Error(`${name} timeline is not an array`)
  }
  for (const item of value) {
    if (item.entity_type !== entityType || item.entity_id !== entityId) {
      throw new Error(`${name} timeline contains another entity`)
    }
  }
}

function assertManagerAuditScope(value, projectIds, forbiddenEntities) {
  assertPage('project_manager audit logs', value)
  if (value.items.some((item) => !projectIds.has(item.project_id))) {
    throw new Error('project_manager audit logs escaped the managed project scope')
  }
  if (value.items.some((item) => forbiddenEntities.has(`${item.entity_type}:${item.entity_id}`))) {
    throw new Error('project_manager audit logs exposed a cross-project entity')
  }
}

const health = await api('/health')
if (health.status !== 'ok') throw new Error('health status is not ok')

const login = await loginAs(username)
const token = login.access_token
if (!token) throw new Error('login response has no access_token')

const projects = await api('/projects?page=1&page_size=20', { token })
assertPage('projects', projects)
if (!projects.items.length) throw new Error('projects list is empty; run backend demo seed')
await api(`/projects/${projects.items[0].id}`, { token })

const ownerCandidates = await api('/users/project-owner-candidates', { token })
const ordinaryRoles = new Set(['operator', 'researcher', 'analyst', 'qa'])
const invalidOwner = ownerCandidates.find((user) => ordinaryRoles.has(user.role))
if (invalidOwner) {
  throw new Error(
    `project owner candidates contains ordinary role: ${invalidOwner.username}/${invalidOwner.role}`,
  )
}

const experiments = await api('/experiment-records?page=1&page_size=20', { token })
assertPage('experiment-records', experiments)
if (!experiments.items.length) {
  throw new Error('experiment-records list is empty; run backend demo seed')
}

const reports = await api('/daily-reports?page=1&page_size=20', { token })
assertPage('daily-reports', reports)
if (!reports.items.length) throw new Error('daily-reports list is empty; run backend demo seed')

const reagents = await api('/reagents?page=1&page_size=100', { token })
assertPage('reagents', reagents)
if (!reagents.items.length) throw new Error('reagents list is empty; run backend demo seed')

const lots = await api('/reagent-lots?page=1&page_size=20', { token })
assertPage('reagent-lots', lots)
if (!lots.items.length) throw new Error('reagent-lots list is empty; run backend demo seed')

const managerLogin = await loginAs('project_manager')
const operatorLogin = await loginAs('operator')
const analystLogin = await loginAs('analyst')
const directorLogin = await loginAs('director')
for (const [name, session] of [
  ['project_manager', managerLogin],
  ['operator', operatorLogin],
  ['analyst', analystLogin],
  ['director', directorLogin],
]) {
  if (!session.access_token) throw new Error(`${name} login response has no access_token`)
}

const managerProjects = await api('/projects?page=1&page_size=20', {
  token: managerLogin.access_token,
})
assertPage('project_manager projects', managerProjects)
if (!managerProjects.items.length) throw new Error('project_manager has no managed project')
const project = managerProjects.items[0]
await api(`/projects/${project.id}`, { token: managerLogin.access_token })

const projectMembers = await api(`/projects/${project.id}/members`, {
  token: managerLogin.access_token,
})
const operator = projectMembers.find((member) => member.user?.username === 'operator')?.user
if (!operator) throw new Error('managed project has no operator member')
const analyst = projectMembers.find((member) => member.user?.username === 'analyst')?.user
if (!analyst) throw new Error('managed project has no analyst member')

const lot = lots.items[0]
const suffix = `${Date.now()}`
const isolatedProject = await api('/projects', {
  token,
  method: 'POST',
  body: {
    project_code: `RC-X-${suffix}`,
    name: 'RC isolated audit project',
    project_type: 'assay',
    lead_user_id: login.user.id,
    status: 'active',
    priority: 'normal',
  },
})
const createdExperiment = await api('/experiment-records', {
  token: operatorLogin.access_token,
  method: 'POST',
  body: {
    project_id: project.id,
    code: `EXP-T14-${suffix}`,
    title: 'T1.4 real flow verification',
    record_type: 'analysis',
    status: 'draft',
    owner_id: operator.id,
    participant_ids: [operator.id],
    objective: 'Verify real experiment field persistence',
    procedure: 'Create, read, update, then dispense',
    result_summary: 'Created by real API verification',
    conclusion: 'Initial conclusion',
    next_step: 'Confirm outbound',
    risk_note: 'Verification-only record',
    reagent_usages: [
      {
        lot_id: lot.id,
        quantity: '0.1000',
        unit: lot.unit,
        purpose: 'analysis',
      },
    ],
  },
})
if (createdExperiment.participant_ids?.[0] !== operator.id) {
  throw new Error('participant_ids did not round-trip')
}
const updatedExperiment = await api(`/experiment-records/${createdExperiment.id}`, {
  token: operatorLogin.access_token,
  method: 'PATCH',
  body: {
    conclusion: 'Verified conclusion',
    next_step: 'Verified next step',
    risk_note: 'Verified risk note',
  },
})
if (
  updatedExperiment.conclusion !== 'Verified conclusion' ||
  updatedExperiment.next_step !== 'Verified next step' ||
  updatedExperiment.risk_note !== 'Verified risk note'
) {
  throw new Error('experiment extended fields did not round-trip')
}
await expectHttp(`/experiment-records/${createdExperiment.id}/dispense`, 403, {
  token: operatorLogin.access_token,
  method: 'POST',
})
const dispensedExperiment = await api(`/experiment-records/${createdExperiment.id}/dispense`, {
  token: managerLogin.access_token,
  method: 'POST',
})
if (!['dispensed', 'insufficient'].includes(dispensedExperiment.reagent_usages[0]?.outbound_status)) {
  throw new Error('experiment usage was not dispensed')
}
const lotTxns = await api(`/inventory-transactions?reagent_lot_id=${lot.id}&page_size=100`, {
  token,
})
assertPage('lot transactions', lotTxns)
if (!lotTxns.items.some((item) => item.source_type === 'experiment' && item.source_id === createdExperiment.id)) {
  throw new Error('experiment inventory transaction is missing')
}
const lotExperiments = await api(`/reagent-lots/${lot.id}/experiments`, { token })
if (!lotExperiments.some((item) => item.experiment_id === createdExperiment.id)) {
  throw new Error('lot detail does not link back to experiment')
}
await expectHttp('/inventory-transactions', 403, {
  token: operatorLogin.access_token,
  method: 'POST',
  body: { reagent_lot_id: lot.id, txn_type: 'in', quantity: '0.1000' },
})
await api('/inventory-transactions', {
  token: directorLogin.access_token,
  method: 'POST',
  body: {
    reagent_lot_id: lot.id,
    txn_type: 'in',
    quantity: '0.1000',
    reference: 'T1.4 real verification replenishment',
  },
})

const report = await api('/daily-reports', {
  token: operatorLogin.access_token,
  method: 'POST',
  body: {
    report_date: new Date().toISOString().slice(0, 10),
    items: [
      {
        project_id: project.id,
        experiment_record_id: createdExperiment.id,
        work_type: 'analysis',
        content: 'Verified experiment real flow',
        problem_note: 'No blocker',
        next_step: 'Review inventory transaction',
        sort_order: 0,
      },
      {
        project_id: project.id,
        work_type: 'documentation',
        content: 'Updated verification notes',
        problem_note: 'None',
        next_step: 'Close T1.4 verification',
        sort_order: 1,
      },
    ],
  },
})
if (report.items?.length !== 2) throw new Error('daily report did not persist multiple items')
await api(`/daily-reports/${report.id}/submit`, {
  token: operatorLogin.access_token,
  method: 'POST',
})
const confirmedReport = await api(`/daily-reports/${report.id}/review`, {
  token: managerLogin.access_token,
  method: 'POST',
  body: { review_comment: 'T1.4 verified' },
})
if (confirmedReport.status !== 'confirmed') throw new Error('daily report was not confirmed')

const method = await api('/test-methods', {
  token,
  method: 'POST',
  body: {
    code: `TM-T15-${suffix}`,
    name: 'T1.5 verification assay',
    category: 'assay',
    version: '1.0',
    description: 'Created by full-stack verification',
  },
})
const sample = await api('/samples', {
  token: managerLogin.access_token,
  method: 'POST',
  body: {
    project_id: project.id,
    sample_no: `S-T15-${suffix}`,
    name: 'T1.5 verification sample',
    type: 'compound',
    source: 'full-stack smoke',
    batch_no: `B-${suffix}`,
    amount: '10.0000',
    unit: 'mg',
    storage_condition: '2-8 C',
  },
})
await expectHttp('/samples', 403, {
  token: directorLogin.access_token,
  method: 'POST',
  body: { project_id: project.id, sample_no: `DENIED-${suffix}`, name: 'Denied' },
})
const task = await api('/test-tasks', {
  token: managerLogin.access_token,
  method: 'POST',
  body: {
    sample_id: sample.id,
    method_id: method.id,
    assigned_to: analyst.id,
    priority: 'high',
  },
})
await api(`/test-tasks/${task.id}/status`, {
  token: analystLogin.access_token,
  method: 'POST',
  body: { status: 'in_progress' },
})
const testResult = await api('/test-results', {
  token: analystLogin.access_token,
  method: 'POST',
  body: {
    task_id: task.id,
    result_data: { assay: 99.5, unit: '%' },
    conclusion: 'Meets specification',
  },
})
const submittedResult = await api(`/test-results/${testResult.id}/submit`, {
  token: analystLogin.access_token,
  method: 'POST',
})
if (submittedResult.status !== 'submitted') throw new Error('T1.5 result was not submitted')
const rejectedResult = await api(`/test-results/${testResult.id}/reject`, {
  token: managerLogin.access_token,
  method: 'POST',
  body: { comment: 'T1.5 full-stack verification rejected for correction' },
})
if (rejectedResult.status !== 'rejected') throw new Error('T1.5 result was not rejected')
const revisedResult = await api(`/test-results/${testResult.id}`, {
  token: analystLogin.access_token,
  method: 'PATCH',
  body: {
    result_data: { assay: 99.7, unit: '%' },
    conclusion: 'Meets specification after correction',
  },
})
if (revisedResult.status !== 'draft' || revisedResult.review_comment !== null) {
  throw new Error('T1.5 rejected result did not return to a clean draft')
}
const resubmittedResult = await api(`/test-results/${testResult.id}/submit`, {
  token: analystLogin.access_token,
  method: 'POST',
})
if (resubmittedResult.status !== 'submitted') {
  throw new Error('T1.5 corrected result was not resubmitted')
}
const approvedResult = await api(`/test-results/${testResult.id}/approve`, {
  token: managerLogin.access_token,
  method: 'POST',
  body: { comment: 'T1.5 full-stack verification approved' },
})
if (approvedResult.status !== 'approved') throw new Error('T1.5 result was not approved')
const completedTask = await api(`/test-tasks/${task.id}`, { token: analystLogin.access_token })
const completedSample = await api(`/samples/${sample.id}`, { token: managerLogin.access_token })
if (completedTask.status !== 'completed' || completedSample.status !== 'completed') {
  throw new Error('T1.5 task/sample did not complete after approval')
}

const adminUsers = await api('/admin/users', { token })
if (!Array.isArray(adminUsers) || !adminUsers.length) {
  throw new Error('admin user list is not a non-empty array')
}
await expectHttp('/admin/users', 403, { token: operatorLogin.access_token })
await expectHttp('/audit-logs?page=1&page_size=10', 403, {
  token: operatorLogin.access_token,
})

const crossExperiment = await api('/experiment-records', {
  token,
  method: 'POST',
  body: {
    project_id: isolatedProject.id,
    code: `EXP-RC-X-${suffix}`,
    title: 'RC cross-project audit experiment',
    record_type: 'analysis',
    status: 'draft',
  },
})
const crossReport = await api('/daily-reports', {
  token,
  method: 'POST',
  body: {
    report_date: new Date().toISOString().slice(0, 10),
    items: [
      {
        project_id: isolatedProject.id,
        work_type: 'analysis',
        content: 'RC cross-project audit report',
        sort_order: 0,
      },
    ],
  },
})
const crossSample = await api('/samples', {
  token,
  method: 'POST',
  body: {
    project_id: isolatedProject.id,
    sample_no: `S-RC-X-${suffix}`,
    name: 'RC cross-project audit sample',
    type: 'compound',
  },
})

for (const [entityType, entityId, memberToken] of [
  ['experiment', createdExperiment.id, operatorLogin.access_token],
  ['daily_report', report.id, operatorLogin.access_token],
  ['sample', sample.id, managerLogin.access_token],
]) {
  const path = `/audit-logs/entity/${entityType}/${entityId}`
  const adminTimeline = await api(path, { token })
  const memberTimeline = await api(path, { token: memberToken })
  assertTimeline(`${entityType} admin`, adminTimeline, entityType, entityId)
  assertTimeline(`${entityType} member`, memberTimeline, entityType, entityId)
  if (!adminTimeline.some((item) => item.action === 'create')) {
    throw new Error(`${entityType} timeline is missing its create audit event`)
  }
}

await expectHttp(`/audit-logs/entity/experiment/${crossExperiment.id}`, 404, {
  token: managerLogin.access_token,
})
await expectHttp(`/audit-logs/entity/daily_report/${crossReport.id}`, 404, {
  token: managerLogin.access_token,
})
await expectHttp(`/audit-logs/entity/sample/${crossSample.id}`, 404, {
  token: managerLogin.access_token,
})

const adminAuditLogs = await api('/audit-logs?page=1&page_size=10', { token })
assertPage('admin audit logs', adminAuditLogs)
const managerAuditLogs = await api('/audit-logs?page=1&page_size=100', {
  token: managerLogin.access_token,
})
assertManagerAuditScope(
  managerAuditLogs,
  new Set(managerProjects.items.map((item) => item.id)),
  new Set([
    `experiment:${crossExperiment.id}`,
    `daily_report:${crossReport.id}`,
    `sample:${crossSample.id}`,
  ]),
)

console.log(
  JSON.stringify(
    {
      base_url: baseUrl,
      health: health.status,
      projects: projects.total,
      owner_candidates: ownerCandidates.length,
      owner_roles: [...new Set(ownerCandidates.map((user) => user.role))],
      experiments: experiments.total,
      daily_reports: reports.total,
      reagents: reagents.total,
      reagent_lots: lots.total,
      real_flow_experiment: createdExperiment.id,
      real_flow_report: report.id,
      real_flow_outbound: dispensedExperiment.reagent_usages[0]?.outbound_status,
      t1_5_sample: sample.id,
      t1_5_task: task.id,
      t1_5_result: approvedResult.id,
      t1_5_status: approvedResult.status,
      admin_users: adminUsers.length,
      admin_audit_logs: adminAuditLogs.total,
      manager_audit_logs: managerAuditLogs.total,
      entity_timelines: ['experiment', 'daily_report', 'sample'],
    },
    null,
    2,
  ),
)
