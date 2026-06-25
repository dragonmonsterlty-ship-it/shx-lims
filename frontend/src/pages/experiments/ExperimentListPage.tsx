import { PlusOutlined } from '@ant-design/icons'
import {
  PageContainer,
  ProTable,
  type ActionType,
  type ProColumns,
} from '@ant-design/pro-components'
import { useQuery } from '@tanstack/react-query'
import { Alert, App, Button, Popconfirm } from 'antd'
import { useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import type { ApiError } from '../../api/errors'
import { USE_MOCK } from '../../api/runtime'
import { useAuth } from '../../auth/useAuth'
import {
  canCreateExperiment,
  canDeleteExperiment,
  canEditExperiment,
} from '../../auth/permissions'
import StatusTag from '../../components/StatusTag'
import { SketchEmpty } from '../../components/sketch'
import { useProjectScope } from '../../hooks/useProjectScope'
import { useUsers } from '../../hooks/useUsers'
import { experimentService } from '../../services/experiment'
import { projectService } from '../../services/project'
import type { Experiment, ExperimentStatus, Id } from '../../types'
import { formatDate, formatDateTime } from '../../utils/format'
import ExperimentFormModal from './ExperimentFormModal'

interface ExperimentParams {
  experiment_no?: string
  title?: string
  project_id?: Id
  status?: ExperimentStatus
  lead_user_id?: Id
  plan_range?: [string, string]
}

const STATUS_OPTIONS = [
  { label: '草稿', value: 'draft' },
  { label: '进行中', value: 'in_progress' },
  { label: '已提交', value: 'submitted' },
  { label: '已审核', value: 'reviewed' },
  { label: '已归档', value: 'archived' },
]

export default function ExperimentListPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const { message } = App.useApp()
  const { getName, data: users } = useUsers()
  const { scope } = useProjectScope(user)
  const actionRef = useRef<ActionType>(null)
  const [loadError, setLoadError] = useState<string>()

  const projectsQuery = useQuery({
    queryKey: ['projects', 'scope-options', user?.id],
    queryFn: () => projectService.listProjects({ page_size: 200 }, user!),
    enabled: !!user,
  })
  const projectMap = useMemo(() => {
    const m = new Map<Id, string>()
    for (const p of projectsQuery.data?.items ?? []) m.set(p.id, `${p.project_code} · ${p.name}`)
    return m
  }, [projectsQuery.data])

  const projectOptions = (projectsQuery.data?.items ?? []).map((p) => ({
    label: `${p.project_code} · ${p.name}`,
    value: p.id,
  }))
  const userOptions = (users ?? []).map((u) => ({ label: u.full_name, value: u.id }))

  if (!user) return null

  const handleDelete = async (id: Id) => {
    try {
      await experimentService.deleteExperiment(id, user.id)
      message.success('实验记录已删除')
      actionRef.current?.reload()
    } catch (error) {
      message.error((error as ApiError).message || '删除失败')
    }
  }

  const columns: ProColumns<Experiment>[] = [
    { title: '实验编号', dataIndex: 'experiment_no', width: 130, fixed: 'left', copyable: true },
    { title: '实验标题', dataIndex: 'title', ellipsis: true },
    {
      title: '所属项目',
      dataIndex: 'project_id',
      width: 180,
      valueType: 'select',
      fieldProps: { options: projectOptions, allowClear: true, showSearch: true, optionFilterProp: 'label' },
      render: (_, row) => projectMap.get(row.project_id) ?? `#${row.project_id}`,
    },
    {
      title: '实验负责人',
      dataIndex: 'lead_user_id',
      width: 110,
      valueType: 'select',
      fieldProps: { options: userOptions, allowClear: true, showSearch: true, optionFilterProp: 'label' },
      render: (_, row) => getName(row.lead_user_id),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueType: 'select',
      fieldProps: { options: STATUS_OPTIONS, allowClear: true },
      render: (_, row) => <StatusTag kind="experiment" value={row.status} />,
    },
    {
      title: '计划日期',
      dataIndex: 'plan_range',
      valueType: 'dateRange',
      width: 200,
      render: (_, row) => `${formatDate(row.plan_start_date)} ~ ${formatDate(row.plan_end_date)}`,
    },
    {
      title: '最近更新',
      dataIndex: 'updated_at',
      width: 150,
      search: false,
      render: (_, row) => formatDateTime(row.updated_at ?? row.created_at),
    },
    {
      title: '操作',
      valueType: 'option',
      width: 150,
      fixed: 'right',
      render: (_, row) => [
        <a key="view" onClick={() => navigate(`/experiments/${row.id}`)}>
          查看
        </a>,
        canEditExperiment(user, row, scope) ? (
          <ExperimentFormModal
            key="edit"
            mode="edit"
            currentUser={user}
            experiment={row}
            trigger={<a>编辑</a>}
            onSaved={() => actionRef.current?.reload()}
          />
        ) : null,
        USE_MOCK && canDeleteExperiment(user.role) ? (
          <Popconfirm
            key="del"
            title="确认删除该实验记录？"
            onConfirm={() => handleDelete(row.id)}
            okText="删除"
            cancelText="取消"
          >
            <a style={{ color: 'var(--ant-color-error, #b4453c)' }}>删除</a>
          </Popconfirm>
        ) : null,
      ],
    },
  ]

  return (
    <PageContainer title="实验记录">
      {loadError ? (
        <Alert
          type="error"
          showIcon
          closable
          message={loadError}
          style={{ marginBottom: 16 }}
          onClose={() => setLoadError(undefined)}
        />
      ) : null}
      <ProTable<Experiment, ExperimentParams>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        scroll={{ x: 1100 }}
        cardBordered
        locale={{ emptyText: <SketchEmpty description="暂无实验记录" /> }}
        options={{ density: true, reload: true, setting: true }}
        pagination={{ defaultPageSize: 10, showSizeChanger: true }}
        search={{ labelWidth: 'auto' }}
        request={async (params) => {
          try {
            setLoadError(undefined)
            const range = params.plan_range
            const res = await experimentService.listExperiments(
              {
                page: params.current,
                page_size: params.pageSize,
                experiment_no: params.experiment_no,
                title: params.title,
                project_id: params.project_id,
                status: params.status,
                lead_user_id: params.lead_user_id,
                plan_date_from: range?.[0],
                plan_date_to: range?.[1],
              },
              user,
            )
            return { data: res.items, total: res.total, success: true }
          } catch (error) {
            setLoadError((error as { message?: string }).message ?? '实验记录加载失败')
            return { data: [], total: 0, success: false }
          }
        }}
        toolBarRender={() =>
          canCreateExperiment(user.role)
            ? [
                <ExperimentFormModal
                  key="create"
                  mode="create"
                  currentUser={user}
                  trigger={
                    <Button type="primary" icon={<PlusOutlined />}>
                      新建实验记录
                    </Button>
                  }
                  onSaved={() => actionRef.current?.reload()}
                />,
              ]
            : []
        }
      />
    </PageContainer>
  )
}
