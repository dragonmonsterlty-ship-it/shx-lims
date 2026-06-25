import { PlusOutlined } from '@ant-design/icons'
import {
  PageContainer,
  ProTable,
  type ActionType,
  type ProColumns,
} from '@ant-design/pro-components'
import { useQuery } from '@tanstack/react-query'
import { Alert, Button, Typography } from 'antd'
import { useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '../../auth/useAuth'
import { canCreateReport, canEditReport } from '../../auth/permissions'
import StatusTag from '../../components/StatusTag'
import { useProjectScope } from '../../hooks/useProjectScope'
import { useUsers } from '../../hooks/useUsers'
import { dailyReportService } from '../../services/dailyReport'
import { experimentService } from '../../services/experiment'
import { projectService } from '../../services/project'
import type { DailyReport, DailyReportStatus, Id } from '../../types'
import { formatDate, formatDateTime } from '../../utils/format'
import DailyReportFormModal from './DailyReportFormModal'
import ReportActions from './ReportActions'

const { Text } = Typography

interface ReportParams {
  date_range?: [string, string]
  user_id?: Id
  project_id?: Id
  related_experiment_id?: Id
  status?: DailyReportStatus
  keyword?: string
}

const STATUS_OPTIONS = [
  { label: '草稿', value: 'draft' },
  { label: '已提交', value: 'submitted' },
  { label: '已退回', value: 'returned' },
  { label: '已确认', value: 'confirmed' },
  { label: '已归档', value: 'archived' },
]

export default function DailyReportListPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const { getName, data: users } = useUsers()
  const { scope } = useProjectScope(user)
  const actionRef = useRef<ActionType>(null)
  const [loadError, setLoadError] = useState<string>()

  const projectsQuery = useQuery({
    queryKey: ['projects', 'scope-options', user?.id],
    queryFn: () => projectService.listProjects({ page_size: 200 }, user!),
    enabled: !!user,
  })
  const experimentsQuery = useQuery({
    queryKey: ['experiments', 'scope-options', user?.id],
    queryFn: () => experimentService.listExperiments({ page_size: 500 }, user!),
    enabled: !!user,
  })

  const projectMap = useMemo(() => {
    const m = new Map<Id, string>()
    for (const p of projectsQuery.data?.items ?? []) m.set(p.id, `${p.project_code} · ${p.name}`)
    return m
  }, [projectsQuery.data])
  const experimentMap = useMemo(() => {
    const m = new Map<Id, string>()
    for (const e of experimentsQuery.data?.items ?? []) m.set(e.id, `${e.experiment_no} · ${e.title}`)
    return m
  }, [experimentsQuery.data])

  const projectOptions = (projectsQuery.data?.items ?? []).map((p) => ({
    label: `${p.project_code} · ${p.name}`,
    value: p.id,
  }))
  const experimentOptions = (experimentsQuery.data?.items ?? []).map((e) => ({
    label: `${e.experiment_no} · ${e.title}`,
    value: e.id,
  }))
  const userOptions = (users ?? []).map((u) => ({ label: u.full_name, value: u.id }))

  if (!user) return null

  const columns: ProColumns<DailyReport>[] = [
    { title: '日期', dataIndex: 'report_date', valueType: 'dateRange', width: 120, render: (_, r) => formatDate(r.report_date), search: { transform: (v) => ({ date_range: v }) } },
    {
      title: '提交人',
      dataIndex: 'user_id',
      width: 100,
      valueType: 'select',
      fieldProps: { options: userOptions, allowClear: true, showSearch: true, optionFilterProp: 'label' },
      render: (_, r) => getName(r.user_id),
    },
    {
      title: '所属项目',
      dataIndex: 'project_id',
      width: 170,
      valueType: 'select',
      fieldProps: { options: projectOptions, allowClear: true, showSearch: true, optionFilterProp: 'label' },
      render: (_, r) =>
        r.project_id != null ? projectMap.get(r.project_id) ?? `#${r.project_id}` : '—',
    },
    {
      title: '关联实验',
      dataIndex: 'related_experiment_id',
      width: 150,
      valueType: 'select',
      fieldProps: { options: experimentOptions, allowClear: true, showSearch: true, optionFilterProp: 'label' },
      render: (_, r) => (r.related_experiment_id ? experimentMap.get(r.related_experiment_id) ?? `#${r.related_experiment_id}` : '—'),
    },
    { title: '工作摘要', dataIndex: 'work_content', ellipsis: true, search: false },
    {
      title: '风险提示',
      dataIndex: 'issues_risks',
      ellipsis: true,
      width: 160,
      search: false,
      render: (_, r) => (r.issues_risks ? <Text type="warning">{r.issues_risks}</Text> : '—'),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      valueType: 'select',
      fieldProps: { options: STATUS_OPTIONS, allowClear: true },
      render: (_, r) => <StatusTag kind="daily_report" value={r.status} />,
    },
    { title: '提交时间', dataIndex: 'submitted_at', width: 150, search: false, render: (_, r) => formatDateTime(r.submitted_at) },
    {
      title: '关键词',
      dataIndex: 'keyword',
      hideInTable: true,
      valueType: 'text',
    },
    {
      title: '操作',
      valueType: 'option',
      width: 170,
      fixed: 'right',
      render: (_, row) => [
        <a key="view" onClick={() => navigate(`/daily-reports/${row.id}`)}>
          查看
        </a>,
        canEditReport(user, row) ? (
          <DailyReportFormModal
            key="edit"
            mode="edit"
            currentUser={user}
            report={row}
            trigger={<a>编辑</a>}
            onSaved={() => actionRef.current?.reload()}
          />
        ) : null,
        <ReportActions key="act" report={row} currentUser={user} scope={scope} onChanged={() => actionRef.current?.reload()} />,
      ],
    },
  ]

  return (
    <PageContainer title="工作日报">
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
      <ProTable<DailyReport, ReportParams>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        scroll={{ x: 1200 }}
        cardBordered
        options={{ density: true, reload: true, setting: true }}
        pagination={{ defaultPageSize: 10, showSizeChanger: true }}
        search={{ labelWidth: 'auto' }}
        request={async (params) => {
          try {
            setLoadError(undefined)
            const range = params.date_range
            const res = await dailyReportService.listReports(
              {
                page: params.current,
                page_size: params.pageSize,
                date_from: range?.[0],
                date_to: range?.[1],
                user_id: params.user_id,
                project_id: params.project_id,
                related_experiment_id: params.related_experiment_id,
                status: params.status,
                keyword: params.keyword,
              },
              user,
            )
            return { data: res.items, total: res.total, success: true }
          } catch (error) {
            setLoadError((error as { message?: string }).message ?? '日报列表加载失败')
            return { data: [], total: 0, success: false }
          }
        }}
        toolBarRender={() =>
          canCreateReport(user.role)
            ? [
                <DailyReportFormModal
                  key="create"
                  mode="create"
                  currentUser={user}
                  trigger={
                    <Button type="primary" icon={<PlusOutlined />}>
                      新建日报
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
