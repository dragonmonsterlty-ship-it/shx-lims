import { LogoutOutlined } from '@ant-design/icons'
import { Button, Card, Col, Empty, Row, Space, Tag, Typography } from 'antd'
import { Navigate, useNavigate } from 'react-router-dom'

import {
  effectiveModules,
  moduleDescription,
  moduleHome,
  moduleLabel,
  moduleSketchIcon,
} from '../../auth/modules'
import { roleLabel } from '../../auth/permissions'
import { useAuth } from '../../auth/useAuth'
import { SketchIcon, type SketchIconName } from '../../components/sketch'
import type { ModuleKey } from '../../types'

const { Title, Text, Paragraph } = Typography

/** 门户角落氛围装饰（视觉宪法白名单：门户属"看一眼"区域，pointer-events:none）。 */
const DECORATIONS: Array<{
  name: SketchIconName
  size: number
  color: string
  opacity: number
  rotate: number
  style: React.CSSProperties
}> = [
  { name: 'flask', size: 96, color: '#4A7C59', opacity: 0.4, rotate: -10, style: { top: '12%', left: '10%' } },
  { name: 'test-tube', size: 84, color: '#2B4C7E', opacity: 0.4, rotate: 12, style: { bottom: '14%', right: '11%' } },
  { name: 'benzene', size: 70, color: '#2B4C7E', opacity: 0.32, rotate: 8, style: { top: '18%', right: '16%' } },
  { name: 'sparkle', size: 34, color: '#C2853B', opacity: 0.55, rotate: 0, style: { bottom: '24%', left: '18%' } },
]

function PortalDecorations() {
  return (
    <div
      aria-hidden
      style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none', zIndex: 0 }}
    >
      {DECORATIONS.map((d, i) => (
        <div
          key={`${d.name}-${i}`}
          style={{ position: 'absolute', opacity: d.opacity, transform: `rotate(${d.rotate}deg)`, ...d.style }}
        >
          <SketchIcon name={d.name} size={d.size} color={d.color} />
        </div>
      ))}
    </div>
  )
}

function ModuleCard({ module, onEnter }: { module: ModuleKey; onEnter: () => void }) {
  return (
    <Card
      hoverable
      onClick={onEnter}
      style={{ borderColor: 'var(--line)', height: '100%' }}
      styles={{ body: { padding: 28 } }}
      aria-label={`进入${moduleLabel[module]}`}
    >
      <Space align="start" size={20} style={{ width: '100%' }}>
        <SketchIcon name={moduleSketchIcon[module]} size={56} color="#2B4C7E" />
        <div style={{ flex: 1 }}>
          <Title level={4} style={{ marginBottom: 8 }}>
            {moduleLabel[module]}
          </Title>
          <Paragraph type="secondary" style={{ marginBottom: 16 }}>
            {moduleDescription[module]}
          </Paragraph>
          <Button type="primary" onClick={onEnter}>
            进入工作区
          </Button>
        </div>
      </Space>
    </Card>
  )
}

export default function PortalPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  if (!user) return <Navigate to="/login" replace />

  const modules = effectiveModules(user)

  // 仅有一个模块时直接重定向进该工作区，不停在门户。
  if (modules.length === 1) {
    return <Navigate to={moduleHome[modules[0]]} replace />
  }

  return (
    <div
      style={{
        position: 'relative',
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
        overflow: 'hidden',
      }}
    >
      <PortalDecorations />
      <div style={{ position: 'absolute', top: 16, right: 24, zIndex: 1 }}>
        <Space>
          <Tag color="blue">{roleLabel[user.role]}</Tag>
          <Button
            type="text"
            icon={<LogoutOutlined />}
            onClick={() => {
              logout()
              navigate('/login', { replace: true })
            }}
          >
            退出登录
          </Button>
        </Space>
      </div>

      <div style={{ position: 'relative', zIndex: 1, width: '100%', maxWidth: 880 }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Title level={2} style={{ marginBottom: 4 }}>
            LIMS
          </Title>
          <Text type="secondary">你好，{user.full_name}，请选择要进入的工作区</Text>
        </div>

        {modules.length === 0 ? (
          <Card style={{ borderColor: 'var(--line)' }}>
            <Empty description="尚未授权任何工作区，请联系管理员开通模块权限。" />
          </Card>
        ) : (
          <Row gutter={[24, 24]} justify="center">
            {modules.map((module) => (
              <Col key={module} xs={24} md={12}>
                <ModuleCard module={module} onEnter={() => navigate(moduleHome[module])} />
              </Col>
            ))}
          </Row>
        )}
      </div>
    </div>
  )
}
