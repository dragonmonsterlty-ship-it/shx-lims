import { PageLoading } from '@ant-design/pro-components'
import { lazy, Suspense, type ReactNode } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'

import AppLayout from '../layouts/AppLayout'
import RequireAuth from './RequireAuth'
import RoleGuard from './RoleGuard'

// 路由级懒加载：按页面拆分代码，减小首屏 bundle。
const LoginPage = lazy(() => import('../pages/auth/LoginPage'))
const DashboardPage = lazy(() => import('../pages/dashboard/DashboardPage'))
const ProjectListPage = lazy(() => import('../pages/projects/ProjectListPage'))
const ProjectDetailPage = lazy(() => import('../pages/projects/ProjectDetailPage'))
const ExperimentListPage = lazy(() => import('../pages/experiments/ExperimentListPage'))
const ExperimentDetailPage = lazy(() => import('../pages/experiments/ExperimentDetailPage'))
const DailyReportListPage = lazy(() => import('../pages/dailyReports/DailyReportListPage'))
const DailyReportDetailPage = lazy(() => import('../pages/dailyReports/DailyReportDetailPage'))
const InventoryListPage = lazy(() => import('../pages/inventory/InventoryListPage'))
const InventoryDetailPage = lazy(() => import('../pages/inventory/InventoryDetailPage'))
const SampleListPage = lazy(() => import('../pages/samples/SampleListPage'))
const SampleDetailPage = lazy(() => import('../pages/samples/SampleDetailPage'))
const TestingReviewPage = lazy(() => import('../pages/testing/TestingReviewPage'))
const AdminPage = lazy(() => import('../pages/admin/AdminPage'))
const ForbiddenPage = lazy(() => import('../pages/error/ForbiddenPage'))
const NotFoundPage = lazy(() => import('../pages/error/NotFoundPage'))

const withSuspense = (node: ReactNode): ReactNode => (
  <Suspense fallback={<PageLoading />}>{node}</Suspense>
)

export const router = createBrowserRouter([
  { path: '/login', element: withSuspense(<LoginPage />) },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { index: true, element: <Navigate to="/dashboard" replace /> },
          { path: 'dashboard', element: withSuspense(<DashboardPage />) },
          { path: 'projects', element: withSuspense(<ProjectListPage />) },
          { path: 'projects/:id', element: withSuspense(<ProjectDetailPage />) },
          { path: 'experiments', element: withSuspense(<ExperimentListPage />) },
          { path: 'experiments/:id', element: withSuspense(<ExperimentDetailPage />) },
          { path: 'daily-reports', element: withSuspense(<DailyReportListPage />) },
          { path: 'daily-reports/:id', element: withSuspense(<DailyReportDetailPage />) },
          { path: 'inventory', element: withSuspense(<InventoryListPage />) },
          { path: 'inventory/:id', element: withSuspense(<InventoryDetailPage />) },
          { path: 'samples', element: withSuspense(<SampleListPage />) },
          { path: 'samples/:id', element: withSuspense(<SampleDetailPage />) },
          { path: 'testing', element: withSuspense(<TestingReviewPage />) },
          {
            element: <RoleGuard allow={['admin']} />,
            children: [{ path: 'admin', element: withSuspense(<AdminPage />) }],
          },
          { path: '403', element: withSuspense(<ForbiddenPage />) },
          { path: '*', element: withSuspense(<NotFoundPage />) },
        ],
      },
    ],
  },
])
