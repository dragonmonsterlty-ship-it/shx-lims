import { AppstoreOutlined, ExperimentOutlined, LogoutOutlined } from '@ant-design/icons'
import { PageLoading, ProLayout } from '@ant-design/pro-components'
import { Dropdown, Tag } from 'antd'
import { createElement } from 'react'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'

import { roleLabel } from '../auth/permissions'
import { useAuth } from '../auth/useAuth'

/**
 * 对照品管理工作区（第二个 ProLayout 实例，独立菜单）。
 * 视觉宪法：工作区内部保持纯 AntD Pro 观感，不引入任何手账元素。
 */
const REFSTD_MENU = [
  { path: '/ref-standards', name: '对照品台账', icon: createElement(ExperimentOutlined) },
]

export default function RefStdLayout() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  if (!user) return <PageLoading />

  return (
    <ProLayout
      title="对照品管理"
      logo={false}
      layout="mix"
      fixedHeader
      fixSiderbar
      contentWidth="Fluid"
      style={{ minHeight: '100vh' }}
      location={{ pathname: location.pathname }}
      route={{ path: '/', routes: REFSTD_MENU }}
      menuItemRender={(item, dom) => (item.path ? <Link to={item.path}>{dom}</Link> : dom)}
      avatarProps={{
        title: user.full_name,
        render: (_props, dom) => (
          <Dropdown
            menu={{
              items: [
                {
                  key: 'role',
                  label: <Tag color="blue">{roleLabel[user.role]}</Tag>,
                  disabled: true,
                },
                { type: 'divider' },
                {
                  key: 'portal',
                  icon: <AppstoreOutlined />,
                  label: '返回门户',
                  onClick: () => navigate('/portal'),
                },
                {
                  key: 'logout',
                  icon: <LogoutOutlined />,
                  label: '退出登录',
                  onClick: () => {
                    logout()
                    navigate('/login', { replace: true })
                  },
                },
              ],
            }}
          >
            {dom}
          </Dropdown>
        ),
      }}
    >
      <Outlet />
    </ProLayout>
  )
}
