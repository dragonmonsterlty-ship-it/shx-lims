import { PageContainer } from '@ant-design/pro-components'
import { useQuery } from '@tanstack/react-query'
import { Button, Descriptions, Empty, Space, Table, Tabs, Timeline, Typography } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'

import { useAuth } from '../../auth/useAuth'
import { canDeleteAttachment, canEditReport, canUploadAttachment } from '../../auth/permissions'
import { AttachmentPanel } from '../../components/attachments'
import QueryBoundary from '../../components/QueryBoundary'
import StatusTag from '../../components/StatusTag'
import { usageRoleLabel } from '../../components/status'
import { useProjectScope } from '../../hooks/useProjectScope'
import { useUsers } from '../../hooks/useUsers'
import { dailyReportService } from '../../services/dailyReport'
import { experimentService } from '../../services/experiment'
import { projectService } from '../../services/project'
import type { DailyReportItem, ExperimentMaterialUsage, Id } from '../../types'
import { formatDate, formatDateTime } from '../../utils/format'
import DailyReportFormModal from './DailyReportFormModal'
import ReportActions from './ReportActions'

const { Paragraph, Text } = Typography

export default function DailyReportDetailPage() {
  const { id } = useParams()
  const reportId = Number(id)
  const { user } = useAuth()
  const navigate = useNavigate()
  const { getName } = useUsers()
  const { scope } = useProjectScope(user)

  const reportQuery = useQuery({
    queryKey: ['report', reportId],
    queryFn: () => dailyReportService.getReport(reportId),
    enabled: Number.isFinite(reportId),
  })
  const report = reportQuery.data

  const projectQuery = useQuery({
    queryKey: ['project', report?.project_id],
    queryFn: () => projectService.getProject(report!.project_id!),
    enabled: report?.project_id != null,
  })
  const expQuery = useQuery({
    queryKey: ['experiment', report?.related_experiment_id],
    queryFn: () => experimentService.getExperiment(report!.related_experiment_id!),
    enabled: !!report?.related_experiment_id,
  })
  const usagesQuery = useQuery({
    queryKey: ['experiment', report?.related_experiment_id, 'usages'],
    queryFn: () => experimentService.listMaterialUsages(report!.related_experiment_id!),
    enabled: !!report?.related_experiment_id,
  })
  const activitiesQuery = useQuery({
    queryKey: ['report', reportId, 'activities'],
    queryFn: () => dailyReportService.listReportActivities(reportId),
    enabled: Number.isFinite(reportId),
  })

  const refetchAll = () => {
    reportQuery.refetch()
    activitiesQuery.refetch()
  }

  const usageColumns = [
    { title: '物料', dataIndex: 'material_name', render: (v: string) => v || '—' },
    { title: '批号', dataIndex: 'batch_no', width: 120, render: (v: string | null) => v ?? '—' },
    { title: '用途', dataIndex: 'usage_role', width: 90, render: (v: string) => usageRoleLabel[v] ?? v },
    { title: '实际用量', dataIndex: 'actual_qty', width: 90, render: (v: number | null) => v ?? '—' },
    { title: '单位', dataIndex: 'unit', width: 70, render: (v: string | null) => v ?? '—' },
    {
      title: '出库状态',
      dataIndex: 'outbound_status',
      width: 100,
      render: (v: string) => <StatusTag kind="dispense" value={v} />,
    },
  ]

  return (
    <PageContainer
      title={report ? `${formatDate(report.report_date)} 日报 · ${getName(report.user_id)}` : '日报详情'}
      onBack={() => navigate('/daily-reports')}
      tags={report ? <StatusTag kind="daily_report" value={report.status} /> : undefined}
      extra={
        report && user ? (
          <Space>
            {canEditReport(user, report) ? (
              <DailyReportFormModal
                mode="edit"
                currentUser={user}
                report={report}
                trigger={<Button>编辑</Button>}
                onSaved={refetchAll}
              />
            ) : null}
            <ReportActions report={report} currentUser={user} scope={scope} onChanged={refetchAll} />
          </Space>
        ) : undefined
      }
    >
      <QueryBoundary loading={reportQuery.isLoading} error={reportQuery.error} onRetry={() => reportQuery.refetch()}>
        {report ? (
          <Tabs
            items={[
              {
                key: 'basic',
                label: '基础信息',
                children: (
                  <Descriptions bordered column={2} size="small">
                    <Descriptions.Item label="日期">{formatDate(report.report_date)}</Descriptions.Item>
                    <Descriptions.Item label="提交人">{getName(report.user_id)}</Descriptions.Item>
                    <Descriptions.Item label="所属项目">
                      {projectQuery.data
                        ? `${projectQuery.data.project_code} · ${projectQuery.data.name}`
                        : report.project_id != null
                          ? `#${report.project_id}`
                          : '—'}
                    </Descriptions.Item>
                    <Descriptions.Item label="关联实验">
                      {expQuery.data ? `${expQuery.data.experiment_no} · ${expQuery.data.title}` : '—'}
                    </Descriptions.Item>
                    <Descriptions.Item label="状态">
                      <StatusTag kind="daily_report" value={report.status} />
                    </Descriptions.Item>
                    <Descriptions.Item label="提交时间">{formatDateTime(report.submitted_at)}</Descriptions.Item>
                    <Descriptions.Item label="确认人">{report.reviewed_by ? getName(report.reviewed_by) : '—'}</Descriptions.Item>
                    <Descriptions.Item label="确认时间">{formatDateTime(report.reviewed_at)}</Descriptions.Item>
                    {report.review_comment ? (
                      <Descriptions.Item label="审核意见" span={2}>
                        {report.review_comment}
                      </Descriptions.Item>
                    ) : null}
                  </Descriptions>
                ),
              },
              {
                key: 'items',
                label: `工作明细（${report.items?.length ?? 0}）`,
                children: (
                  <Table<DailyReportItem>
                    rowKey="id"
                    size="small"
                    dataSource={report.items ?? []}
                    pagination={false}
                    columns={[
                      { title: '工作内容', dataIndex: 'content', render: (v: string) => <Paragraph>{v}</Paragraph> },
                      { title: '问题/风险', dataIndex: 'problem_note', render: (v: string | null) => v || '—' },
                      { title: '明日计划', dataIndex: 'next_step', render: (v: string | null) => v || '—' },
                      {
                        title: '关联实验',
                        dataIndex: 'experiment_record_id',
                        width: 110,
                        render: (v: Id | null) =>
                          v ? <a onClick={() => navigate(`/experiments/${v}`)}>实验 #{v}</a> : '—',
                      },
                    ]}
                    locale={{ emptyText: '暂无工作明细' }}
                  />
                ),
              },
              {
                key: 'experiment',
                label: '关联实验摘要',
                children: expQuery.data ? (
                  <Space direction="vertical" style={{ width: '100%' }} size="middle">
                    <Descriptions bordered column={2} size="small">
                      <Descriptions.Item label="实验编号">{expQuery.data.experiment_no}</Descriptions.Item>
                      <Descriptions.Item label="实验标题">{expQuery.data.title}</Descriptions.Item>
                      <Descriptions.Item label="状态">
                        <StatusTag kind="experiment" value={expQuery.data.status} />
                      </Descriptions.Item>
                      <Descriptions.Item label="实验负责人">{getName(expQuery.data.lead_user_id)}</Descriptions.Item>
                    </Descriptions>
                    <div>
                      <Text strong>物料消耗摘要</Text>
                      {usagesQuery.data && usagesQuery.data.length ? (
                        <Table<ExperimentMaterialUsage>
                          rowKey="id"
                          size="small"
                          style={{ marginTop: 8 }}
                          dataSource={usagesQuery.data}
                          columns={usageColumns}
                          pagination={false}
                        />
                      ) : (
                        <Paragraph type="secondary" style={{ marginTop: 8 }}>
                          物料消耗摘要后续接入
                        </Paragraph>
                      )}
                    </div>
                  </Space>
                ) : (
                  <Empty description="未关联实验记录" />
                ),
              },
              {
                key: 'attachments',
                label: '附件/图谱',
                children:
                  user && report.project_id != null ? (
                    <AttachmentPanel
                      entityType="daily_report"
                      entityId={report.id}
                      canUpload={canUploadAttachment(
                        user,
                        {
                          entityType: 'daily_report',
                          projectId: report.project_id,
                          editable: report.status === 'draft' || report.status === 'returned',
                          ownerId: report.user_id,
                        },
                        scope,
                      )}
                      canDelete={(attachment) =>
                        canDeleteAttachment(
                          user,
                          attachment,
                          {
                            entityType: 'daily_report',
                            projectId: report.project_id!,
                            editable: report.status === 'draft' || report.status === 'returned',
                            ownerId: report.user_id,
                          },
                          scope,
                        )
                      }
                    />
                  ) : (
                    <Empty description="该日报未关联唯一项目，不能上传项目归属型附件" />
                  ),
              },
              {
                key: 'activity',
                label: '操作记录',
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
                  <Empty description="暂无操作记录" />
                ),
              },
            ]}
          />
        ) : null}
      </QueryBoundary>
    </PageContainer>
  )
}
