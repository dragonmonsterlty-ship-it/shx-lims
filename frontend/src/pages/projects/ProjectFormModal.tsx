import {
  ModalForm,
  ProFormDatePicker,
  ProFormSelect,
  ProFormText,
  ProFormTextArea,
} from '@ant-design/pro-components'
import { App } from 'antd'
import dayjs from 'dayjs'
import type { ReactNode } from 'react'

import type { ApiError } from '../../api/errors'
import { canEditProject, isOwnerRole } from '../../auth/permissions'
import { projectService } from '../../services/project'
import { userService } from '../../services/user'
import type { Project, ProjectInput, User } from '../../types'

interface ProjectFormModalProps {
  mode: 'create' | 'edit'
  currentUser: User
  project?: Project
  trigger: ReactNode
  onSaved?: () => void
}

interface FormValues extends Omit<ProjectInput, 'start_date' | 'end_date'> {
  start_date?: string | dayjs.Dayjs | null
  end_date?: string | dayjs.Dayjs | null
}

const toDate = (v?: string | dayjs.Dayjs | null): string | null =>
  v ? dayjs(v).format('YYYY-MM-DD') : null

export default function ProjectFormModal({
  mode,
  currentUser,
  project,
  trigger,
  onSaved,
}: ProjectFormModalProps) {
  const { message } = App.useApp()
  const isEdit = mode === 'edit'
  // project_manager 的负责人锁定为本人（新建与编辑均不可改）。
  const lockOwner = currentUser.role === 'pm' || currentUser.role === 'project_manager'

  // 编辑时异步载入当前组员，作为初始值。
  const editRequest = async (): Promise<FormValues> => {
    const members = await projectService.listMembers(project!.id)
    return {
      project_code: project!.project_code,
      name: project!.name,
      project_type: project!.project_type ?? undefined,
      lead_user_id: project!.lead_user_id ?? undefined,
      status: project!.status,
      description: project!.description ?? undefined,
      start_date: project!.start_date ?? undefined,
      end_date: project!.end_date ?? undefined,
      member_ids: members.filter((m) => m.role_in_project === 'member').map((m) => m.user_id),
    }
  }

  const createInitial: FormValues = {
    project_code: '',
    name: '',
    status: 'active',
    lead_user_id: lockOwner ? currentUser.id : undefined,
    member_ids: [],
  }

  return (
    <ModalForm<FormValues>
      title={isEdit ? '编辑项目' : '新建项目'}
      trigger={<span>{trigger}</span>}
      modalProps={{ destroyOnHidden: true }}
      {...(isEdit ? { request: editRequest } : { initialValues: createInitial })}
      onFinish={async (values) => {
        // 二次角色校验：不仅靠 UI 隐藏按钮。
        if (!isEdit && !isOwnerRole(currentUser.role)) {
          message.error('当前角色无权新建项目')
          return false
        }
        if (isEdit && project && !canEditProject(currentUser, project)) {
          message.error('无权编辑该项目（仅负责人或管理员可编辑）')
          return false
        }
        // project_manager 强制负责人为本人。
        const leadId = lockOwner ? currentUser.id : (values.lead_user_id ?? null)
        const payload: ProjectInput = {
          project_code: values.project_code,
          name: values.name,
          project_type: values.project_type ?? null,
          lead_user_id: leadId,
          status: values.status,
          description: values.description ?? null,
          start_date: toDate(values.start_date),
          end_date: toDate(values.end_date),
          member_ids: values.member_ids ?? [],
        }
        try {
          if (isEdit && project) {
            await projectService.updateProject(project.id, payload, currentUser.id)
            message.success('项目已更新')
          } else {
            await projectService.createProject(payload, currentUser.id)
            message.success('项目已创建')
          }
          onSaved?.()
          return true
        } catch (error) {
          message.error((error as ApiError).message || '保存失败')
          return false
        }
      }}
    >
      <ProFormText
        name="project_code"
        label="项目代码"
        rules={[{ required: true, message: '请输入项目代码' }]}
        fieldProps={{ disabled: isEdit }}
        tooltip="全局唯一，参与样品编号生成"
      />
      <ProFormText name="name" label="项目名称" rules={[{ required: true, message: '请输入项目名称' }]} />
      <ProFormSelect
        name="project_type"
        label="项目类型"
        options={[
          { label: '稳定性', value: '稳定性' },
          { label: '质量研究', value: '质量研究' },
          { label: '工艺', value: '工艺' },
          { label: '小试路线', value: '小试路线' },
        ]}
        fieldProps={{ allowClear: true }}
      />
      <ProFormSelect
        name="lead_user_id"
        label="项目负责人"
        showSearch
        disabled={lockOwner}
        tooltip={
          lockOwner
            ? '项目主管新建/编辑项目时，负责人锁定为本人'
            : '仅项目主管及以上角色可担任；保存后自动登记为项目 manager'
        }
        rules={[{ required: true, message: '请选择项目负责人' }]}
        request={async () => {
          if (lockOwner) {
            return [{ label: `${currentUser.full_name}（${currentUser.username}）`, value: currentUser.id }]
          }
          const users = await userService.listProjectOwnerCandidates()
          return users
            .map((u) => ({ label: `${u.full_name}（${u.username}）`, value: u.id }))
        }}
      />
      <ProFormSelect
        name="member_ids"
        label="项目组员"
        mode="multiple"
        fieldProps={{ allowClear: true, optionFilterProp: 'label', placeholder: '选择操作员作为组员（可多选）' }}
        tooltip="项目组员/实验员，通常为操作员（operator）；负责人无需在此重复添加"
        request={async () => {
          const users = await userService.listUsers()
          return users
            .filter((u) => u.role === 'operator')
            .map((u) => ({ label: `${u.full_name}（${u.username}）`, value: u.id }))
        }}
      />
      <ProFormSelect
        name="status"
        label="项目状态"
        initialValue="active"
        options={[
          { label: '进行中', value: 'active' },
          { label: '暂停', value: 'paused' },
          { label: '已完成', value: 'completed' },
          { label: '已终止', value: 'cancelled' },
        ]}
        rules={[{ required: true }]}
      />
      <ProFormDatePicker name="start_date" label="开始日期" />
      <ProFormDatePicker name="end_date" label="结束日期" />
      <ProFormTextArea name="description" label="项目描述" fieldProps={{ rows: 3 }} />
    </ModalForm>
  )
}
