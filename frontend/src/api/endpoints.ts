// 真实后端路径集中定义。baseURL 已包含 /api。

export const endpoints = {
  health: '/health',
  auth: {
    login: '/auth/login',
    refresh: '/auth/refresh',
    logout: '/auth/logout',
    changePassword: '/auth/change-password',
  },
  users: {
    me: '/users/me',
    list: '/users',
    projectOwnerCandidates: '/users/project-owner-candidates',
  },
  projects: {
    root: '/projects',
    detail: (id: number) => `/projects/${id}`,
    summary: (id: number) => `/projects/${id}/summary`,
    members: (id: number) => `/projects/${id}/members`,
    member: (id: number, userId: number) => `/projects/${id}/members/${userId}`,
  },
  dailyReports: {
    root: '/daily-reports',
    detail: (id: number) => `/daily-reports/${id}`,
    submit: (id: number) => `/daily-reports/${id}/submit`,
    review: (id: number) => `/daily-reports/${id}/review`,
    return: (id: number) => `/daily-reports/${id}/return`,
    archive: (id: number) => `/daily-reports/${id}/archive`,
  },
  attachments: {
    upload: '/attachments/upload',
    detail: (id: number) => `/attachments/${id}`,
    download: (id: number) => `/attachments/${id}/download`,
  },
  reagents: {
    root: '/reagents',
    detail: (id: number) => `/reagents/${id}`,
    lots: '/reagent-lots',
    lot: (id: number) => `/reagent-lots/${id}`,
    lotExperiments: (id: number) => `/reagent-lots/${id}/experiments`,
    lowStockLots: '/reagent-lots/low-stock',
    txns: '/inventory-transactions',
    txn: (id: number) => `/inventory-transactions/${id}`,
  },
  experiments: {
    root: '/experiment-records',
    detail: (id: number) => `/experiment-records/${id}`,
    submit: (id: number) => `/experiment-records/${id}/submit`,
    archive: (id: number) => `/experiment-records/${id}/archive`,
    dispense: (id: number) => `/experiment-records/${id}/dispense`,
  },
  samples: { root: '/samples', detail: (id: number) => `/samples/${id}`, tests: (id: number) => `/samples/${id}/tests` },
  results: { root: '/results', review: (id: number) => `/results/${id}/review` },
} as const
