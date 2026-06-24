import { LockOutlined, UserOutlined } from '@ant-design/icons'
import { App, Button, Card, Form, Input, Typography } from 'antd'
import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'

import type { ApiError } from '../../api/errors'
import { USE_MOCK } from '../../api/runtime'
import { useAuth } from '../../auth/useAuth'

const { Title, Text, Paragraph } = Typography

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
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--paper)',
        padding: 24,
      }}
    >
      <Card style={{ width: 380, borderColor: 'var(--line)' }} variant="outlined">
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
                  { u: 'director', label: '主任' },
                  { u: 'pm', label: '项目主管' },
                  { u: 'op', label: '操作员' },
                ]
              : [
                  { u: 'pm', label: '项目负责人' },
                  { u: 'project_manager', label: '项目主管' },
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
