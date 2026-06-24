import {
  EditableProTable,
  ModalForm,
  ProFormDateRangePicker,
  ProFormDependency,
  ProFormSelect,
  ProFormText,
  ProFormTextArea,
  type ProColumns,
  type ProFormInstance,
} from '@ant-design/pro-components'
import { useQuery } from '@tanstack/react-query'
import { App, Divider, Typography } from 'antd'
import dayjs from 'dayjs'
import { useEffect, useRef, useState, type Key, type ReactNode } from 'react'

import type { ApiError } from '../../api/errors'
import { roleLabel } from '../../auth/permissions'
import { USAGE_ROLE_OPTIONS } from '../../components/status'
import { experimentService } from '../../services/experiment'
import { inventoryService } from '../../services/inventory'
import { projectService } from '../../services/project'
import type {
  Experiment,
  ExperimentInput,
  Id,
  MaterialUsageInput,
  UsageRole,
  User,
} from '../../types'

const { Text } = Typography

interface ExperimentFormModalProps {
  mode: 'create' | 'edit'
  currentUser: User
  experiment?: Experiment
  trigger: ReactNode
  onSaved?: () => void
}

interface FormValues {
  experiment_no?: string
  project_id?: Id
  title: string
  lead_user_id?: Id
  participant_ids?: Id[]
  status: Experiment['status']
  plan_range?: [string, string] | null
  objective?: string
  steps?: string
  result_summary?: string
}

interface UsageRow {
  key: Key
  id?: Id
  batch_id?: Id
  usage_role: UsageRole
  planned_qty?: number
  actual_qty?: number
  remark?: string
}

const STATUS_OPTIONS = [
  { label: '草稿', value: 'draft' },
  { label: '计划中', value: 'planned' },
  { label: '进行中', value: 'in_progress' },
  { label: '已完成', value: 'completed' },
  { label: '已取消', value: 'cancelled' },
]

export default function ExperimentFormModal({
  mode,
  currentUser,
  experiment,
  trigger,
  onSaved,
}: ExperimentFormModalProps) {
  const { message } = App.useApp()
  const isEdit = mode === 'edit'
  const formRef = useRef<ProFormInstance>(null)
  const isOperator = currentUser.role === 'operator'

  const [usages, setUsages] = useState<UsageRow[]>([])
  const [editableKeys, setEditableKeys] = useState<Key[]>([])

  const matQuery = useQuery({
    queryKey: ['inventory', 'materials-batches'],
    queryFn: async () => {
      const [materials, batches] = await Promise.all([
        inventoryService.listMaterials(),
        inventoryService.listAllBatches(),
      ])
      return { materials, batches }
    },
  })

  const materialMap = new Map((matQuery.data?.materials ?? []).map((m) => [m.id, m]))
  const batchMap = new Map((matQuery.data?.batches ?? []).map((b) => [b.id, b]))
  const batchOptions = (matQuery.data?.batches ?? []).map((b) => ({
    label: `${materialMap.get(b.material_id)?.name ?? ''} / ${b.batch_no}（库存 ${b.quantity}${b.unit}）`,
    value: b.id,
  }))

  const usagesQuery = useQuery({
    queryKey: ['experiment', experiment?.id, 'usages-pending'],
    queryFn: () => experimentService.listMaterialUsages(experiment!.id),
    enabled: isEdit && !!experiment,
  })
  useEffect(() => {
    if (!usagesQuery.data) return
    const rows: UsageRow[] = usagesQuery.data
      .filter((u) => u.outbound_status === 'pending')
      .map((u) => ({
        key: u.id,
        id: u.id,
        batch_id: u.batch_id ?? undefined,
        usage_role: u.usage_role,
        planned_qty: u.planned_qty ?? undefined,
        actual_qty: u.actual_qty ?? undefined,
        remark: u.remark ?? undefined,
      }))
    setUsages(rows)
    setEditableKeys(rows.map((r) => r.key))
  }, [usagesQuery.data])

  const initialValues: FormValues =
    isEdit && experiment
      ? {
          experiment_no: experiment.experiment_no,
          project_id: experiment.project_id,
          title: experiment.title,
          lead_user_id: experiment.lead_user_id,
          participant_ids: experiment.participant_ids,
          status: experiment.status,
          plan_range:
            experiment.plan_start_date && experiment.plan_end_date
              ? [experiment.plan_start_date, experiment.plan_end_date]
              : null,
          objective: experiment.objective ?? undefined,
          steps: experiment.steps ?? undefined,
          result_summary: experiment.result_summary ?? undefined,
        }
      : { title: '', status: 'draft', participant_ids: [], lead_user_id: isOperator ? currentUser.id : undefined }

  const projectOptions = async () => {
    const res = await projectService.listProjects({ page_size: 200 }, currentUser)
    return res.items.map((p) => ({ label: `${p.project_code} · ${p.name}`, value: p.id }))
  }

  const memberOptions = async (projectId?: Id) => {
    if (!projectId) return []
    const members = await projectService.listMembers(projectId)
    return members.map((m) => ({
      label: `${m.user?.full_name ?? `#${m.user_id}`}（${m.user ? roleLabel[m.user.role] : '成员'}）`,
      value: m.user_id,
    }))
  }

  const usageColumns: ProColumns<UsageRow>[] = [
    {
      title: '物料 / 批号',
      dataIndex: 'batch_id',
      valueType: 'select',
      width: 240,
      fieldProps: { options: batchOptions, showSearch: true, optionFilterProp: 'label' },
      formItemProps: { rules: [{ required: true, message: '请选择物料/批号' }] },
    },
    {
      title: '用途',
      dataIndex: 'usage_role',
      valueType: 'select',
      width: 120,
      fieldProps: { options: USAGE_ROLE_OPTIONS },
      formItemProps: { rules: [{ required: true, message: '请选择用途' }] },
    },
    { title: '计划用量', dataIndex: 'planned_qty', valueType: 'digit', width: 100 },
    { title: '实际用量', dataIndex: 'actual_qty', valueType: 'digit', width: 100 },
    {
      title: '当前库存',
      dataIndex: 'stock_view',
      editable: false,
      width: 130,
      render: (_, record) => {
        const batch = record.batch_id ? batchMap.get(record.batch_id) : undefined
        if (!batch) return <Text type="secondary">未关联</Text>
        const insufficient = (record.actual_qty ?? 0) > batch.quantity
        return (
          <span style={{ color: insufficient ? '#b4453c' : undefined }}>
            {batch.quantity}
            {batch.unit}
            {insufficient ? `（缺口 ${(record.actual_qty ?? 0) - batch.quantity}）` : ''}
          </span>
        )
      },
    },
    { title: '备注', dataIndex: 'remark', valueType: 'text', width: 140 },
    {
      title: '操作',
      valueType: 'option',
      width: 70,
      render: (_, row) => [
        <a key="del" onClick={() => setUsages((prev) => prev.filter((r) => r.key !== row.key))}>
          删除
        </a>,
      ],
    },
  ]

  return (
    <ModalForm<FormValues>
      title={isEdit ? '编辑实验记录' : '新建实验记录'}
      trigger={<span>{trigger}</span>}
      formRef={formRef}
      width={760}
      modalProps={{ destroyOnHidden: true }}
      initialValues={initialValues}
      onFinish={async (values) => {
        const range = values.plan_range
        const material_usages: MaterialUsageInput[] = usages.map((r) => ({
          id: typeof r.id === 'number' ? r.id : undefined,
          batch_id: r.batch_id ?? null,
          usage_role: r.usage_role,
          planned_qty: r.planned_qty ?? null,
          actual_qty: r.actual_qty ?? null,
          remark: r.remark ?? null,
        }))
        const payload: ExperimentInput = {
          project_id: values.project_id!,
          experiment_no: values.experiment_no?.trim() || undefined,
          title: values.title,
          lead_user_id: values.lead_user_id!,
          participant_ids: values.participant_ids ?? [],
          status: values.status,
          plan_start_date: range?.[0] ? dayjs(range[0]).format('YYYY-MM-DD') : null,
          plan_end_date: range?.[1] ? dayjs(range[1]).format('YYYY-MM-DD') : null,
          objective: values.objective ?? null,
          steps: values.steps ?? null,
          result_summary: values.result_summary ?? null,
          material_usages,
        }
        try {
          if (isEdit && experiment) {
            await experimentService.updateExperiment(experiment.id, payload, currentUser.id)
            message.success('实验记录已更新')
          } else {
            await experimentService.createExperiment(payload, currentUser.id)
            message.success('实验记录已创建')
          }
          onSaved?.()
          return true
        } catch (error) {
          message.error((error as ApiError).message || '保存失败')
          return false
        }
      }}
    >
      <ProFormText name="experiment_no" label="实验编号" placeholder="留空自动生成" tooltip="可手动指定，需全局唯一" />
      <ProFormSelect
        name="project_id"
        label="所属项目"
        rules={[{ required: true, message: '请选择所属项目' }]}
        request={projectOptions}
        disabled={isEdit}
        fieldProps={{
          showSearch: true,
          optionFilterProp: 'label',
          onChange: () => {
            formRef.current?.setFieldsValue({
              lead_user_id: isOperator ? currentUser.id : undefined,
              participant_ids: [],
            })
          },
        }}
        tooltip="仅可选择你可见（负责或参与）的项目"
      />
      <ProFormText name="title" label="实验标题" rules={[{ required: true, message: '请输入实验标题' }]} />
      <ProFormDependency name={['project_id']}>
        {({ project_id }) => (
          <>
            <ProFormSelect
              name="lead_user_id"
              label="实验负责人"
              rules={[{ required: true, message: '请选择实验负责人' }]}
              disabled={!project_id}
              params={{ project_id }}
              request={async () => memberOptions(project_id)}
              fieldProps={{ showSearch: true, optionFilterProp: 'label' }}
              tooltip="从该项目的负责人与成员中选择"
            />
            <ProFormSelect
              name="participant_ids"
              label="实验参与人"
              mode="multiple"
              disabled={!project_id}
              params={{ project_id }}
              request={async () => memberOptions(project_id)}
              fieldProps={{ allowClear: true, optionFilterProp: 'label' }}
              tooltip="从该项目成员中多选"
            />
          </>
        )}
      </ProFormDependency>
      <ProFormSelect name="status" label="实验状态" options={STATUS_OPTIONS} rules={[{ required: true }]} />
      <ProFormDateRangePicker name="plan_range" label="计划日期" />
      <ProFormTextArea name="objective" label="实验目的" fieldProps={{ rows: 2 }} />
      <ProFormTextArea name="steps" label="实验步骤" fieldProps={{ rows: 4 }} />
      <ProFormTextArea name="result_summary" label="结果摘要" fieldProps={{ rows: 2 }} />

      <Divider orientation="left" plain>
        物料使用（保存不扣库存；出库在详情页确认）
      </Divider>
      <EditableProTable<UsageRow>
        rowKey="key"
        value={usages}
        onChange={(rows) => setUsages(rows as UsageRow[])}
        controlled
        loading={matQuery.isLoading}
        columns={usageColumns}
        scroll={{ x: 760 }}
        rowClassName={(record) => {
          const batch = record.batch_id ? batchMap.get(record.batch_id) : undefined
          return batch && (record.actual_qty ?? 0) > batch.quantity ? 'lims-row-warning' : ''
        }}
        recordCreatorProps={{
          position: 'bottom',
          creatorButtonText: '添加物料行',
          record: () => ({ key: `new-${Date.now()}`, usage_role: 'reagent' }),
        }}
        editable={{
          type: 'multiple',
          editableKeys,
          onChange: setEditableKeys,
          actionRender: (_row, _config, dom) => [dom.delete],
        }}
      />
    </ModalForm>
  )
}
