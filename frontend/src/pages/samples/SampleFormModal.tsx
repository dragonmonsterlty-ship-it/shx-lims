import {
  ModalForm,
  ProFormDatePicker,
  ProFormDigit,
  ProFormSelect,
  ProFormText,
  ProFormTextArea,
} from '@ant-design/pro-components'
import { App } from 'antd'
import type { ReactNode } from 'react'

import type { ApiError } from '../../api/errors'
import { projectService } from '../../services/project'
import { sampleService } from '../../services/sample'
import type { Sample, SampleInput, User } from '../../types'

interface Props {
  mode: 'create' | 'edit'
  currentUser: User
  sample?: Sample
  trigger: ReactNode
  onSaved?: () => void
}

export default function SampleFormModal({ mode, currentUser, sample, trigger, onSaved }: Props) {
  const { message } = App.useApp()
  const isEdit = mode === 'edit'

  return (
    <ModalForm<SampleInput>
      title={isEdit ? '编辑样品' : '新建样品'}
      width={620}
      trigger={<span>{trigger}</span>}
      modalProps={{ destroyOnHidden: true }}
      initialValues={
        sample
          ? {
              project_id: sample.project_id,
              sample_no: sample.sample_no,
              name: sample.name,
              type: sample.type,
              source: sample.source,
              batch_no: sample.batch_no,
              amount: sample.amount,
              unit: sample.unit,
              storage_condition: sample.storage_condition,
              priority: sample.priority,
              due_date: sample.due_date,
              notes: sample.notes,
            }
          : { priority: 'normal' }
      }
      onFinish={async (values) => {
        try {
          if (isEdit && sample) await sampleService.updateSample(sample.id, values)
          else await sampleService.createSample(values)
          message.success(isEdit ? '样品已更新' : '样品已创建')
          onSaved?.()
          return true
        } catch (error) {
          message.error((error as ApiError).message || '保存失败')
          return false
        }
      }}
    >
      <ProFormSelect
        name="project_id"
        label="所属项目"
        disabled={isEdit}
        rules={[{ required: true, message: '请选择所属项目' }]}
        request={async () => {
          const page = await projectService.listProjects({ page_size: 100 }, currentUser)
          return page.items.map((project) => ({
            label: `${project.project_code} · ${project.name}`,
            value: project.id,
          }))
        }}
        fieldProps={{ showSearch: true, optionFilterProp: 'label' }}
      />
      <ProFormText
        name="sample_no"
        label="样品编号"
        disabled={isEdit}
        rules={[{ required: true, message: '请输入样品编号' }]}
      />
      <ProFormText name="name" label="样品名称" rules={[{ required: true, message: '请输入样品名称' }]} />
      <ProFormText name="type" label="样品类型" />
      <ProFormText name="source" label="来源" />
      <ProFormText name="batch_no" label="批号" />
      <ProFormDigit name="amount" label="数量" min={0} fieldProps={{ precision: 4 }} />
      <ProFormText name="unit" label="单位" />
      <ProFormText name="storage_condition" label="储存条件" />
      <ProFormSelect
        name="priority"
        label="优先级"
        options={[
          { label: '普通', value: 'normal' },
          { label: '加急', value: 'urgent' },
        ]}
      />
      <ProFormDatePicker name="due_date" label="截止日期" />
      <ProFormTextArea name="notes" label="备注" fieldProps={{ rows: 3 }} />
    </ModalForm>
  )
}
