import { LockOutlined, UserOutlined } from '@ant-design/icons'
import { App, Button, Card, Form, Input, Typography } from 'antd'
import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'

import type { ApiError } from '../../api/errors'
import { USE_MOCK } from '../../api/runtime'
import { useAuth } from '../../auth/useAuth'
import { SketchIcon, type SketchIconName } from '../../components/sketch'

const { Title, Text, Paragraph } = Typography

/** 仅作氛围的角落手账装饰（白名单：登录页背景）。绝不进入登录卡片本身。 */
const DECORATIONS: Array<{
  name: SketchIconName
  size: number
  color: string
  opacity: number
  rotate: number
  style: React.CSSProperties
}> = [
  { name: 'test-tube', size: 84, color: '#2B4C7E', opacity: 0.5, rotate: -12, style: { top: '12%', left: '14%' } },
  { name: 'flask', size: 100, color: '#4A7C59', opacity: 0.42, rotate: 8, style: { bottom: '12%', left: '10%' } },
  { name: 'brain-ai', size: 92, color: '#2B4C7E', opacity: 0.46, rotate: 10, style: { top: '14%', right: '13%' } },
  { name: 'laptop', size: 96, color: '#333', opacity: 0.34, rotate: -6, style: { bottom: '14%', right: '12%' } },
  { name: 'reagent', size: 64, color: '#4A7C59', opacity: 0.36, rotate: 14, style: { bottom: '30%', right: '26%' } },
  { name: 'qrcode', size: 60, color: '#333', opacity: 0.3, rotate: -8, style: { top: '34%', left: '26%' } },
  { name: 'sparkle', size: 40, color: '#C2853B', opacity: 0.6, rotate: 0, style: { top: '24%', left: '46%' } },
  { name: 'sparkle', size: 30, color: '#2B4C7E', opacity: 0.5, rotate: 0, style: { bottom: '22%', left: '40%' } },
  { name: 'sparkle', size: 34, color: '#4A7C59', opacity: 0.5, rotate: 0, style: { top: '60%', right: '20%' } },
]

function LoginDecorations() {
  return (
    <div
      aria-hidden
      style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none', zIndex: 0 }}
    >
      {DECORATIONS.map((d, i) => (
        <div
          key={`${d.name}-${i}`}
          style={{
            position: 'absolute',
            opacity: d.opacity,
            transform: `rotate(${d.rotate}deg)`,
            ...d.style,
          }}
        >
          <SketchIcon name={d.name} size={d.size} color={d.color} />
        </div>
      ))}
    </div>
  )
}

interface LoginValues {
  username: string
  password: string
}

export default function LoginPage() {
  const { isAuthenticated, login } = useAuth()
  const { message } = App.useApp()
  const navigate = useNavigate()
  const location = useLocation()
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm<LoginValues>()

  const from = (location.state as { from?: string } | null)?.from ?? '/dashboard'

  if (isAuthenticated) {
    return <Navigate to={from} replace />
  }

  const onFinish = async (values: LoginValues) => {
    setLoading(true)
    try {
      await login(values.username, values.password)
      message.success('登录成功')
      navigate(from, { replace: true })
    } catch (error) {
      message.error((error as ApiError).message || '登录失败')
    } finally {
      setLoading(false)
    }
  }

  const quickFill = (username: string) => {
    form.setFieldsValue({ username, password: USE_MOCK ? 'demo' : 'password123' })
  }

  return (
    <div
      style={{
        position: 'relative',
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'transparent',
        padding: 24,
        overflow: 'hidden',
      }}
    >
      <LoginDecorations />
      <Card
        style={{ width: 380, borderColor: 'var(--line)', position: 'relative', zIndex: 1 }}
        variant="outlined"
      >
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Title level={3} style={{ marginBottom: 4 }}>
            LIMS
          </Title>
          <Text type="secondary">实验室信息管理系统</Text>
        </div>
        <Form form={form} layout="vertical" onFinish={onFinish} requiredMark={false}>
          <Form.Item
            name="username"
            label="用户名"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input prefix={<UserOutlined />} placeholder="用户名" autoComplete="username" />
          </Form.Item>
          <Form.Item
            name="password"
            label="密码"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="密码"
              autoComplete="current-password"
            />
          </Form.Item>
          <Form.Item style={{ marginBottom: 8 }}>
            <Button type="primary" htmlType="submit" block loading={loading}>
              登录
            </Button>
          </Form.Item>
        </Form>
        <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 4 }}>
          {USE_MOCK ? 'Mock 演示账号（任意密码）：' : '后端 Demo 账号（密码 password123）：'}
        </Paragraph>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {[
            { u: 'admin', label: '管理员' },
            ...(USE_MOCK
              ? [
                  { u: 'director', label: '主管' },
                  { u: 'project_manager', label: '项目负责人' },
                  { u: 'op', label: '操作员' },
                ]
              : [
                  { u: 'director', label: '主管' },
                  { u: 'project_manager', label: '项目负责人' },
                  { u: 'operator', label: '操作员' },
                ]),
          ].map((item) => (
            <Button key={item.u} size="small" onClick={() => quickFill(item.u)}>
              {item.label}
            </Button>
          ))}
        </div>
      </Card>
    </div>
  )
}
