import {
  AuditOutlined,
  ContainerOutlined,
  DashboardOutlined,
  ExperimentOutlined,
  FileTextOutlined,
  MedicineBoxOutlined,
  ProjectOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { createElement, type ReactNode } from 'react'

import type { Role } from '../types'

export interface AppMenuItem {
  path: string
  name: string
  icon?: ReactNode
  /** 限定可见角色；省略表示所有已登录角色可见。 */
  roles?: Role[]
}

const ALL_MENU: AppMenuItem[] = [
  { path: '/dashboard', name: '仪表盘', icon: createElement(DashboardOutlined) },
  { path: '/projects', name: '项目管理', icon: createElement(ProjectOutlined) },
  { path: '/daily-reports', name: '工作日报', icon: createElement(FileTextOutlined) },
  { path: '/experiments', name: '实验记录', icon: createElement(ExperimentOutlined) },
  { path: '/samples', name: '样品管理', icon: createElement(ContainerOutlined) },
  { path: '/testing', name: '检测与审核', icon: createElement(AuditOutlined) },
  { path: '/inventory', name: '试剂库存', icon: createElement(MedicineBoxOutlined) },
  {
    path: '/admin/users',
    name: '管理员管理',
    icon: createElement(SettingOutlined),
    roles: ['admin'],
  },
  {
    path: '/audit-logs',
    name: '审计日志',
    icon: createElement(SafetyCertificateOutlined),
    roles: ['admin', 'project_manager'],
  },
]

export function buildMenu(role: Role): AppMenuItem[] {
  return ALL_MENU.filter((item) => !item.roles || item.roles.includes(role))
}
