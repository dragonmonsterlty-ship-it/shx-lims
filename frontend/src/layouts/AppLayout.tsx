import { LogoutOutlined, SearchOutlined } from '@ant-design/icons'
import { PageLoading, ProLayout } from '@ant-design/pro-components'
import { Alert, Dropdown, Input, Tag } from 'antd'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../auth/useAuth'
import { roleLabel } from '../auth/permissions'
import { buildMenu } from './menu'

export default function AppLayout() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  if (!user) return <PageLoading />

  const menuData = buildMenu(user.role)

  return (
    <ProLayout
      title="LIMS"
      logo={false}
      layout="mix"
      fixedHeader
      fixSiderbar
      contentWidth="Fluid"
      style={{ minHeight: '100vh' }}
      location={{ pathname: location.pathname }}
      route={{ path: '/', routes: menuData }}
      menuItemRender={(item, dom) =>
        item.path ? <Link to={item.path}>{dom}</Link> : dom
      }
      actionsRender={() => [
        <Input
          key="search"
          prefix={<SearchOutlined />}
          placeholder="全局搜索（占位）"
          disabled
          style={{ width: 200 }}
        />,
      ]}
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
      {user.must_change_password ? (
        <Alert
          type="warning"
          showIcon
          closable
          banner
          message="首次登录建议尽快修改初始密码（完整改密流程后续提供）。"
          style={{ marginBottom: 16 }}
        />
      ) : null}
      <Outlet />
    </ProLayout>
  )
}
