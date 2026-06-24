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

const health = await api('/health')
if (health.status !== 'ok') throw new Error('health status is not ok')

const login = await api('/auth/login', {
  method: 'POST',
  body: { username, password },
})
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
    },
    null,
    2,
  ),
)
