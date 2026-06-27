import {
  PageContainer,
  ProTable,
  type ActionType,
  type ProColumns,
} from '@ant-design/pro-components'
import { App, Button, Form, Input, Modal, Popconfirm, Select, Space, Tag } from 'antd'
import { useRef, useState } from 'react'

import type { ApiError } from '../../api/errors'
import { roleLabel } from '../../auth/permissions'
import { SketchEmpty } from '../../components/sketch'
import {
  listAdminUsers,
  resetUserPassword,
  updateUserRole,
  updateUserStatus,
} from '../../services/admin'
import type { AdminUser, UserRole } from '../../types'

const ROLE_OPTIONS: { label: string; value: UserRole }[] = (
  ['admin', 'director', 'project_manager', 'researcher', 'operator', 'viewer'] as UserRole[]
).map((role) => ({ label: roleLabel[role], value: role }))

interface ResetPasswordForm {
  new_password: string
}

export default function AdminUsersPage() {
  const actionRef = useRef<ActionType>(null)
  const { message, modal } = App.useApp()
  const [resetTarget, setResetTarget] = useState<AdminUser | null>(null)
  const [resetting, setResetting] = useState(false)
  const [form] = Form.useForm<ResetPasswordForm>()

  const reload = () => actionRef.current?.reload()
  const showError = (error: unknown, fallback: string) => {
    message.error((error as { message?: string }).message ?? fallback)
  }

  const changeRole = (user: AdminUser, role: UserRole) => {
    if (role === user.role) return
    modal.confirm({
      title: '确认修改用户角色？',
      content: `${user.full_name}：${roleLabel[user.role]} → ${roleLabel[role]}`,
      okText: '确认修改',
      cancelText: '取消',
      onOk: async () => {
        try {
          await updateUserRole(user.id, role)
          message.success('用户角色已更新')
          reload()
        } catch (error) {
          showError(error, '角色修改失败')
          throw error
        }
      },
    })
  }

  const submitResetPassword = async ({ new_password }: ResetPasswordForm) => {
    if (!resetTarget) return
    setResetting(true)
    try {
      await resetUserPassword(resetTarget.id, new_password)
      message.success('密码已重置，用户下次登录时必须修改密码')
      setResetTarget(null)
      form.resetFields()
      reload()
    } catch (error) {
      const apiError = error as ApiError
      if (apiError.fieldErrors?.new_password) {
        form.setFields([
          { name: 'new_password', errors: [apiError.fieldErrors.new_password] },
        ])
      } else {
        message.error(apiError.message || '密码重置失败')
      }
    } finally {
      setResetting(false)
    }
  }

  const columns: ProColumns<AdminUser>[] = [
    { title: '用户名', dataIndex: 'username', width: 140, copyable: true },
    { title: '姓名', dataIndex: 'full_name', width: 140 },
    { title: '邮箱', dataIndex: 'email', ellipsis: true, renderText: (value) => value || '—' },
    {
      title: '角色',
      dataIndex: 'role',
      width: 170,
      render: (_, user) => (
        <Select<UserRole>
          aria-label={`修改 ${user.username} 的角色`}
          value={user.role}
          options={ROLE_OPTIONS}
          style={{ width: 150 }}
          onChange={(role) => changeRole(user, role)}
        />
      ),
    },
    {
      title: '部门',
      dataIndex: 'department',
      width: 140,
      renderText: (value) => value || '—',
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      width: 90,
      render: (_, user) =>
        user.is_active ? <Tag color="success">已启用</Tag> : <Tag>已禁用</Tag>,
    },
    {
      title: '改密要求',
      dataIndex: 'must_change_password',
      width: 110,
      render: (_, user) =>
        user.must_change_password ? <Tag color="warning">需要改密</Tag> : '否',
    },
    {
      title: '操作',
      valueType: 'option',
      width: 190,
      fixed: 'right',
      render: (_, user) => (
        <Space>
          <Popconfirm
            title={`确认${user.is_active ? '禁用' : '启用'}该用户？`}
            description={user.is_active ? '禁用后该用户将无法登录。' : undefined}
            okButtonProps={{ danger: user.is_active }}
            onConfirm={async () => {
              try {
                await updateUserStatus(user.id, !user.is_active)
                message.success(`用户已${user.is_active ? '禁用' : '启用'}`)
                reload()
              } catch (error) {
                showError(error, '用户状态更新失败')
              }
            }}
          >
            <a>{user.is_active ? '禁用' : '启用'}</a>
          </Popconfirm>
          <Button
            type="link"
            size="small"
            onClick={() => {
              form.resetFields()
              setResetTarget(user)
            }}
          >
            重置密码
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <PageContainer title="管理员管理">
      <ProTable<AdminUser>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={false}
        pagination={false}
        options={{ density: true, reload: true, setting: true }}
        scroll={{ x: 1120 }}
        locale={{ emptyText: <SketchEmpty description="暂无用户" /> }}
        request={async () => {
          try {
            return { data: await listAdminUsers(), success: true }
          } catch (error) {
            showError(error, '用户列表加载失败')
            return { data: [], success: false }
          }
        }}
      />

      <Modal
        title={`重置密码${resetTarget ? `：${resetTarget.full_name}` : ''}`}
        open={!!resetTarget}
        confirmLoading={resetting}
        okText="确认重置"
        cancelText="取消"
        onOk={() => form.submit()}
        onCancel={() => {
          setResetTarget(null)
          form.resetFields()
        }}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={submitResetPassword}>
          <Form.Item
            name="new_password"
            label="新密码"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 8, message: '新密码至少 8 位' },
            ]}
          >
            <Input.Password autoComplete="new-password" placeholder="至少 8 位" />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  )
}
