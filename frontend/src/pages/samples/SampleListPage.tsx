import {
  PageContainer,
  ProTable,
  type ActionType,
  type ProColumns,
} from '@ant-design/pro-components'
import { useQuery } from '@tanstack/react-query'
import { Alert } from 'antd'
import { useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '../../auth/useAuth'
import StatusTag from '../../components/StatusTag'
import { SketchEmpty } from '../../components/sketch'
import { projectService } from '../../services/project'
import { sampleService } from '../../services/sample'
import type { Id, Sample, SamplePriority, SampleStatus } from '../../types'
import { formatDate, formatDateTime } from '../../utils/format'

interface SampleParams {
  keyword?: string
  project_id?: Id
  status?: SampleStatus
  priority?: SamplePriority
}

const STATUS_OPTIONS = [
  { label: '已登记', value: 'registered' },
  { label: '检测中', value: 'in_testing' },
  { label: '待审核', value: 'pending_review' },
  { label: '已完成', value: 'completed' },
  { label: '已作废', value: 'cancelled' },
]

const PRIORITY_OPTIONS = [
  { label: '普通', value: 'normal' },
  { label: '加急', value: 'urgent' },
]

export default function SampleListPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
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

  if (!user) return null

  const columns: ProColumns<Sample>[] = [
    { title: '样品编码', dataIndex: 'sample_code', width: 140, fixed: 'left', copyable: true, search: false },
    {
      title: '关键词',
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: { placeholder: '样品编码 / 名称 / 化合物' },
    },
    { title: '样品名称', dataIndex: 'name', ellipsis: true, search: false },
    { title: '化合物', dataIndex: 'compound_name', width: 140, ellipsis: true, search: false },
    {
      title: '所属项目',
      dataIndex: 'project_id',
      width: 200,
      valueType: 'select',
      fieldProps: { options: projectOptions, allowClear: true, showSearch: true, optionFilterProp: 'label' },
      render: (_, row) => projectMap.get(row.project_id) ?? `#${row.project_id}`,
    },
    { title: '类型', dataIndex: 'sample_type', width: 100, search: false, render: (_, row) => row.sample_type ?? '—' },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueType: 'select',
      fieldProps: { options: STATUS_OPTIONS, allowClear: true },
      render: (_, row) => <StatusTag kind="sample" value={row.status} />,
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      width: 90,
      valueType: 'select',
      fieldProps: { options: PRIORITY_OPTIONS, allowClear: true },
      render: (_, row) =>
        row.priority === 'urgent' ? (
          <StatusTag kind="batch" value="low" />
        ) : (
          <span style={{ color: 'var(--ink-muted)' }}>普通</span>
        ),
    },
    {
      title: '截止日期',
      dataIndex: 'due_date',
      width: 110,
      search: false,
      render: (_, row) => formatDate(row.due_date),
    },
    {
      title: '收样时间',
      dataIndex: 'received_at',
      width: 150,
      search: false,
      render: (_, row) => formatDateTime(row.received_at),
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
      width: 80,
      fixed: 'right',
      render: (_, row) => [
        <a key="view" onClick={() => navigate(`/samples/${row.id}`)}>
          查看
        </a>,
      ],
    },
  ]

  return (
    <PageContainer title="样品管理">
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
      <ProTable<Sample, SampleParams>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        scroll={{ x: 1200 }}
        cardBordered
        locale={{ emptyText: <SketchEmpty description="暂无样品记录" /> }}
        options={{ density: true, reload: true, setting: true }}
        pagination={{ defaultPageSize: 10, showSizeChanger: true }}
        search={{ labelWidth: 'auto' }}
        request={async (params) => {
          try {
            setLoadError(undefined)
            const res = await sampleService.listSamples(
              {
                page: params.current,
                page_size: params.pageSize,
                keyword: params.keyword,
                project_id: params.project_id,
                status: params.status,
                priority: params.priority,
              },
              user,
            )
            return { data: res.items, total: res.total, success: true }
          } catch (error) {
            setLoadError((error as { message?: string }).message ?? '样品列表加载失败')
            return { data: [], total: 0, success: false }
          }
        }}
      />
    </PageContainer>
  )
}
