import { PageContainer } from '@ant-design/pro-components'
import { useQuery } from '@tanstack/react-query'
import {
  Alert,
  App,
  Button,
  Descriptions,
  Empty,
  Popconfirm,
  Space,
  Table,
  Tabs,
  Timeline,
  Tooltip,
  Typography,
} from 'antd'
import { useNavigate, useParams } from 'react-router-dom'

import type { ApiError } from '../../api/errors'
import { USE_MOCK } from '../../api/runtime'
import { useAuth } from '../../auth/useAuth'
import { canDispenseMaterials, canEditExperiment } from '../../auth/permissions'
import QueryBoundary from '../../components/QueryBoundary'
import StatusTag from '../../components/StatusTag'
import { usageRoleLabel } from '../../components/status'
import { useProjectScope } from '../../hooks/useProjectScope'
import { useUsers } from '../../hooks/useUsers'
import { experimentService } from '../../services/experiment'
import { projectService } from '../../services/project'
import type { Attachment, ExperimentMaterialUsage, Id } from '../../types'
import { formatDate, formatDateTime, formatFileSize } from '../../utils/format'
import ExperimentFormModal from './ExperimentFormModal'

const { Paragraph, Text } = Typography

export default function ExperimentDetailPage() {
  const { id } = useParams()
  const experimentId = Number(id)
  const { user } = useAuth()
  const navigate = useNavigate()
  const { getName } = useUsers()
  const { scope } = useProjectScope(user)
  const { message } = App.useApp()

  const expQuery = useQuery({
    queryKey: ['experiment', experimentId],
    queryFn: () => experimentService.getExperiment(experimentId),
    enabled: Number.isFinite(experimentId),
  })
  const exp = expQuery.data

  const projectQuery = useQuery({
    queryKey: ['project', exp?.project_id],
    queryFn: () => projectService.getProject(exp!.project_id),
    enabled: !!exp,
  })
  const activitiesQuery = useQuery({
    queryKey: ['experiment', experimentId, 'activities'],
    queryFn: () => experimentService.listExperimentActivities(experimentId),
    enabled: Number.isFinite(experimentId),
  })
  const attachmentsQuery = useQuery({
    queryKey: ['experiment', experimentId, 'attachments'],
    queryFn: () => experimentService.listExperimentAttachments(experimentId),
    enabled: Number.isFinite(experimentId),
  })
  const usagesQuery = useQuery({
    queryKey: ['experiment', experimentId, 'usages'],
    queryFn: () => experimentService.listMaterialUsages(experimentId),
    enabled: Number.isFinite(experimentId),
  })

  const usages = usagesQuery.data ?? []
  const hasPending = usages.some((u) => u.outbound_status === 'pending')
  const canDispense = !!exp && !!user && canDispenseMaterials(user, exp, scope)

  const handleDispense = async () => {
    if (!exp || !user) return
    try {
      await experimentService.dispenseMaterials(exp.id, user.id)
      message.success('已确认出库，库存已按实际用量扣减')
      usagesQuery.refetch()
      activitiesQuery.refetch()
    } catch (error) {
      message.error((error as ApiError).message || '出库失败')
    }
  }

  const usageColumns = [
    { title: '物料名称', dataIndex: 'material_name', render: (v: string) => v || '—' },
    { title: '批号', dataIndex: 'batch_no', width: 130, render: (v: string | null) => v ?? '—' },
    {
      title: '用途',
      dataIndex: 'usage_role',
      width: 90,
      render: (v: string) => usageRoleLabel[v] ?? v,
    },
    { title: '计划用量', dataIndex: 'planned_qty', width: 90, render: (v: number | null) => v ?? '—' },
    { title: '实际用量', dataIndex: 'actual_qty', width: 90, render: (v: number | null) => v ?? '—' },
    { title: '单位', dataIndex: 'unit', width: 70, render: (v: string | null) => v ?? '—' },
    {
      title: '当前库存',
      dataIndex: 'stock_available',
      width: 120,
      render: (v: number | null, row: ExperimentMaterialUsage) =>
        v == null ? '—' : `${v}${row.unit ?? ''}${row.shortage_qty ? `（缺口 ${row.shortage_qty}）` : ''}`,
    },
    {
      title: '库存状态',
      dataIndex: 'stock_status',
      width: 110,
      render: (v: string) => <StatusTag kind="material_stock" value={v} />,
    },
    {
      title: '出库状态',
      dataIndex: 'outbound_status',
      width: 110,
      render: (v: string) => <StatusTag kind="dispense" value={v} />,
    },
  ]

  const participantNames =
    exp && exp.participant_ids.length
      ? exp.participant_ids.map((pid) => getName(pid)).join('、')
      : '—'

  const attachmentColumns = [
    { title: '文件名', dataIndex: 'original_filename', ellipsis: true },
    { title: '类型', dataIndex: 'content_type', width: 160, render: (v: string | null) => v ?? '—' },
    { title: '大小', dataIndex: 'file_size', width: 100, render: (v: number | null) => formatFileSize(v) },
    { title: '上传人', dataIndex: 'uploaded_by', width: 110, render: (v: Id | null) => getName(v) },
    { title: '上传时间', dataIndex: 'uploaded_at', width: 160, render: (v: string) => formatDateTime(v) },
    {
      title: '操作',
      key: 'op',
      width: 140,
      render: () => (
        <Space>
          <Tooltip title="占位：mock 附件，暂不支持下载">
            <a style={{ color: 'var(--ink-muted)' }}>下载</a>
          </Tooltip>
          <Tooltip title="占位：mock 附件，暂不支持预览">
            <a style={{ color: 'var(--ink-muted)' }}>预览</a>
          </Tooltip>
        </Space>
      ),
    },
  ]

  return (
    <PageContainer
      title={exp ? `${exp.experiment_no} · ${exp.title}` : '实验记录详情'}
      onBack={() => navigate('/experiments')}
      tags={exp ? <StatusTag kind="experiment" value={exp.status} /> : undefined}
      extra={
        exp && user && canEditExperiment(user, exp, scope)
          ? [
              <ExperimentFormModal
                key="edit"
                mode="edit"
                currentUser={user}
                experiment={exp}
                trigger={<Button type="primary">编辑</Button>}
                onSaved={() => {
                  expQuery.refetch()
                  activitiesQuery.refetch()
                }}
              />,
            ]
          : undefined
      }
    >
      <QueryBoundary loading={expQuery.isLoading} error={expQuery.error} onRetry={() => expQuery.refetch()}>
        {exp ? (
          <Tabs
            items={[
              {
                key: 'basic',
                label: '基础信息',
                children: (
                  <Descriptions bordered column={2} size="small">
                    <Descriptions.Item label="实验编号">{exp.experiment_no}</Descriptions.Item>
                    <Descriptions.Item label="实验标题">{exp.title}</Descriptions.Item>
                    <Descriptions.Item label="所属项目">
                      {projectQuery.data ? `${projectQuery.data.project_code} · ${projectQuery.data.name}` : `#${exp.project_id}`}
                    </Descriptions.Item>
                    <Descriptions.Item label="实验负责人">{getName(exp.lead_user_id)}</Descriptions.Item>
                    <Descriptions.Item label="实验参与人" span={2}>
                      {participantNames}
                    </Descriptions.Item>
                    <Descriptions.Item label="状态">
                      <StatusTag kind="experiment" value={exp.status} />
                    </Descriptions.Item>
                    <Descriptions.Item label="计划日期">
                      {formatDate(exp.plan_start_date)} ~ {formatDate(exp.plan_end_date)}
                    </Descriptions.Item>
                    <Descriptions.Item label="最近更新" span={2}>
                      {formatDateTime(exp.updated_at ?? exp.created_at)}
                    </Descriptions.Item>
                  </Descriptions>
                ),
              },
              {
                key: 'objective',
                label: '实验目的',
                children: <Paragraph style={{ whiteSpace: 'pre-wrap' }}>{exp.objective || '—'}</Paragraph>,
              },
              {
                key: 'steps',
                label: '实验步骤',
                children: <Paragraph style={{ whiteSpace: 'pre-wrap' }}>{exp.steps || '—'}</Paragraph>,
              },
              {
                key: 'result',
                label: '结果摘要',
                children: <Paragraph style={{ whiteSpace: 'pre-wrap' }}>{exp.result_summary || '—'}</Paragraph>,
              },
              {
                key: 'conclusion',
                label: '结论与后续',
                children: (
                  <Descriptions bordered column={1} size="small">
                    <Descriptions.Item label="实验结论">{exp.conclusion || '—'}</Descriptions.Item>
                    <Descriptions.Item label="下一步">{exp.next_step || '—'}</Descriptions.Item>
                    <Descriptions.Item label="风险备注">{exp.risk_note || '—'}</Descriptions.Item>
                  </Descriptions>
                ),
              },
              {
                key: 'materials',
                label: '物料使用',
                children: (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Space>
                      {canDispense ? (
                        <Popconfirm
                          title="确认按实际用量出库并扣减库存？已出库行不会重复扣减。"
                          onConfirm={handleDispense}
                          okText="确认出库"
                          cancelText="取消"
                          disabled={!hasPending}
                        >
                          <Button type="primary" disabled={!hasPending}>
                            确认出库
                          </Button>
                        </Popconfirm>
                      ) : (
                        <Text type="secondary">仅项目负责人及以上可确认出库</Text>
                      )}
                      {!hasPending ? <Text type="secondary">当前无待出库物料</Text> : null}
                    </Space>
                    <Table<ExperimentMaterialUsage>
                      rowKey="id"
                      size="small"
                      loading={usagesQuery.isLoading}
                      dataSource={usages}
                      columns={usageColumns}
                      pagination={false}
                      locale={{ emptyText: '暂无物料使用' }}
                      rowClassName={(r) => (r.stock_status === 'insufficient' ? 'lims-row-warning' : '')}
                    />
                  </Space>
                ),
              },
              {
                key: 'attachments',
                label: '附件/图谱',
                children: (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Alert
                      type="info"
                      showIcon
                      message={
                        USE_MOCK
                          ? '附件为 mock 占位数据，暂不支持下载/预览。'
                          : '当前后端仅返回附件元数据，本轮不扩展真实文件上传/下载。'
                      }
                    />
                    <Table<Attachment>
                      rowKey="id"
                      size="small"
                      loading={attachmentsQuery.isLoading}
                      dataSource={attachmentsQuery.data ?? []}
                      columns={attachmentColumns}
                      locale={{ emptyText: '暂无附件' }}
                      pagination={false}
                    />
                  </Space>
                ),
              },
              {
                key: 'activity',
                label: '操作日志',
                children: activitiesQuery.data?.length ? (
                  <Timeline
                    items={activitiesQuery.data.map((a) => ({
                      children: (
                        <Space>
                          <Text>{a.action}</Text>
                          <Text type="secondary">
                            {getName(a.actor_id)} · {formatDateTime(a.at)}
                          </Text>
                        </Space>
                      ),
                    }))}
                  />
                ) : (
                  <Empty description="暂无操作日志" />
                ),
              },
            ]}
          />
        ) : null}
      </QueryBoundary>
    </PageContainer>
  )
}
