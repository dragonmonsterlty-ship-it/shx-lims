import {
  PageContainer,
  ProTable,
  type ActionType,
  type ProColumns,
} from '@ant-design/pro-components'
import { PlusOutlined } from '@ant-design/icons'
import { App, Button, Form, Input, Modal, Popconfirm, Select, Space, Switch, Tag } from 'antd'
import { useRef, useState } from 'react'

import type { ApiError } from '../../api/errors'
import { MODULE_OPTIONS, effectiveModules, moduleLabel } from '../../auth/modules'
import { roleLabel } from '../../auth/permissions'
import { SketchEmpty } from '../../components/sketch'
import {
  createAdminUser,
  listAdminUsers,
  resetUserPassword,
  updateUserModules,
  updateUserRole,
  updateUserStatus,
} from '../../services/admin'
import type { AdminUser, AdminUserCreate, ModuleKey, UserRole } from '../../types'

const ROLE_OPTIONS: { label: string; value: UserRole }[] = (
  ['admin', 'director', 'project_manager', 'researcher', 'operator', 'viewer'] as UserRole[]
).map((role) => ({ label: roleLabel[role], value: role }))

interface ResetPasswordForm {
  new_password: string
}

interface ModulesForm {
  modules: ModuleKey[]
}

type CreateAccountForm = AdminUserCreate

export default function AdminUsersPage() {
  const actionRef = useRef<ActionType>(null)
  const { message, modal } = App.useApp()
  const [createOpen, setCreateOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [resetTarget, setResetTarget] = useState<AdminUser | null>(null)
  const [resetting, setResetting] = useState(false)
  const [modulesTarget, setModulesTarget] = useState<AdminUser | null>(null)
  const [savingModules, setSavingModules] = useState(false)
  const [createForm] = Form.useForm<CreateAccountForm>()
  const [resetForm] = Form.useForm<ResetPasswordForm>()
  const [modulesForm] = Form.useForm<ModulesForm>()

  const reload = () => actionRef.current?.reload()
  const showError = (error: unknown, fallback: string) => {
    message.error((error as { message?: string }).message ?? fallback)
  }

  const closeCreateModal = () => {
    setCreateOpen(false)
    createForm.resetFields()
  }

  const submitCreateAccount = async (values: CreateAccountForm) => {
    setCreating(true)
    try {
      await createAdminUser({
        ...values,
        username: values.username.trim(),
        display_name: values.display_name.trim(),
        email: values.email?.trim() || undefined,
      })
      message.success('账号创建成功')
      closeCreateModal()
      reload()
    } catch (error) {
      const apiError = error as ApiError
      if (
        apiError.status === 409 ||
        apiError.fieldErrors?.username ||
        /username|用户名/i.test(apiError.message)
      ) {
        const duplicateMessage = apiError.fieldErrors?.username || '用户名已存在'
        createForm.setFields([{ name: 'username', errors: [duplicateMessage] }])
        message.error(duplicateMessage)
      } else if (apiError.status === 403) {
        message.error('权限不足，仅系统管理员可以添加账号')
      } else {
        message.error('账号创建失败，请稍后重试')
      }
    } finally {
      setCreating(false)
    }
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
      resetForm.resetFields()
      reload()
    } catch (error) {
      const apiError = error as ApiError
      if (apiError.fieldErrors?.new_password) {
        resetForm.setFields([
          { name: 'new_password', errors: [apiError.fieldErrors.new_password] },
        ])
      } else {
        message.error(apiError.message || '密码重置失败')
      }
    } finally {
      setResetting(false)
    }
  }

  const openModulesModal = (user: AdminUser) => {
    setModulesTarget(user)
    modulesForm.setFieldsValue({ modules: effectiveModules(user) })
  }

  const submitModules = async ({ modules }: ModulesForm) => {
    if (!modulesTarget) return
    setSavingModules(true)
    try {
      await updateUserModules(modulesTarget.id, modules)
      message.success('可访问模块已更新')
      setModulesTarget(null)
      modulesForm.resetFields()
      reload()
    } catch (error) {
      const apiError = error as ApiError
      if (apiError.status === 403) {
        message.error('权限不足，仅系统管理员可以修改模块')
      } else {
        message.error(apiError.message || '模块修改失败')
      }
    } finally {
      setSavingModules(false)
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
      title: '可访问模块',
      dataIndex: 'modules',
      width: 200,
      render: (_, user) => (
        <Space size={4} wrap>
          {effectiveModules(user).map((module) => (
            <Tag key={module} color={module === 'refstd' ? 'purple' : 'geekblue'}>
              {moduleLabel[module]}
            </Tag>
          ))}
        </Space>
      ),
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
      width: 260,
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
          <Button type="link" size="small" onClick={() => openModulesModal(user)}>
            修改模块
          </Button>
          <Button
            type="link"
            size="small"
            onClick={() => {
              resetForm.resetFields()
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
        toolBarRender={() => [
          <Button
            key="create-account"
            type="primary"
            icon={<PlusOutlined />}
            aria-label="添加账号"
            onClick={() => {
              createForm.resetFields()
              setCreateOpen(true)
            }}
          >
            添加账号
          </Button>,
        ]}
        pagination={false}
        options={{ density: true, reload: true, setting: true }}
        scroll={{ x: 1360 }}
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
        title="添加账号"
        open={createOpen}
        confirmLoading={creating}
        okText="创建账号"
        cancelText="取消"
        onOk={() => createForm.submit()}
        onCancel={closeCreateModal}
        destroyOnHidden
      >
        <Form<CreateAccountForm>
          form={createForm}
          layout="vertical"
          initialValues={{ is_active: true, modules: ['lims'] }}
          onFinish={submitCreateAccount}
        >
          <Form.Item
            name="username"
            label="用户名"
            rules={[
              { required: true, message: '请输入用户名' },
              { whitespace: true, message: '用户名不能为空' },
            ]}
          >
            <Input autoComplete="username" maxLength={50} />
          </Form.Item>
          <Form.Item
            name="display_name"
            label="显示名"
            rules={[
              { required: true, message: '请输入显示名' },
              { whitespace: true, message: '显示名不能为空' },
            ]}
          >
            <Input maxLength={100} />
          </Form.Item>
          <Form.Item
            name="email"
            label="邮箱"
            rules={[{ type: 'email', message: '请输入有效的邮箱地址' }]}
          >
            <Input autoComplete="email" maxLength={120} />
          </Form.Item>
          <Form.Item
            name="password"
            label="初始密码"
            rules={[
              { required: true, message: '请输入初始密码' },
              { min: 8, message: '初始密码至少 8 位' },
            ]}
          >
            <Input.Password autoComplete="new-password" maxLength={255} placeholder="至少 8 位" />
          </Form.Item>
          <Form.Item
            name="role"
            label="角色"
            rules={[{ required: true, message: '请选择角色' }]}
          >
            <Select<UserRole> options={ROLE_OPTIONS} placeholder="请选择角色" />
          </Form.Item>
          <Form.Item
            name="modules"
            label="可访问模块"
            tooltip="决定该用户可进入哪些工作区；系统管理员默认拥有全部模块。"
            rules={[{ required: true, message: '请至少选择一个模块' }]}
          >
            <Select<ModuleKey[]>
              mode="multiple"
              options={MODULE_OPTIONS}
              placeholder="请选择可访问模块"
            />
          </Form.Item>
          <Form.Item name="is_active" label="是否启用" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`重置密码${resetTarget ? `：${resetTarget.full_name}` : ''}`}
        open={!!resetTarget}
        confirmLoading={resetting}
        okText="确认重置"
        cancelText="取消"
        onOk={() => resetForm.submit()}
        onCancel={() => {
          setResetTarget(null)
          resetForm.resetFields()
        }}
        destroyOnHidden
      >
        <Form form={resetForm} layout="vertical" onFinish={submitResetPassword}>
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

      <Modal
        title={`修改可访问模块${modulesTarget ? `：${modulesTarget.full_name}` : ''}`}
        open={!!modulesTarget}
        confirmLoading={savingModules}
        okText="保存"
        cancelText="取消"
        onOk={() => modulesForm.submit()}
        onCancel={() => {
          setModulesTarget(null)
          modulesForm.resetFields()
        }}
        destroyOnHidden
      >
        <Form form={modulesForm} layout="vertical" onFinish={submitModules}>
          <Form.Item
            name="modules"
            label="可访问模块"
            tooltip="系统管理员默认拥有全部模块，修改对其不生效。"
            rules={[{ required: true, message: '请至少选择一个模块' }]}
          >
            <Select<ModuleKey[]>
              mode="multiple"
              options={MODULE_OPTIONS}
              placeholder="请选择可访问模块"
            />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  )
}
