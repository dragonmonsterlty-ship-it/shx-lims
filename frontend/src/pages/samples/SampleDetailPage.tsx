import { PageContainer } from '@ant-design/pro-components'
import { useQuery } from '@tanstack/react-query'
import { Button, Card, Descriptions, Space, Table, Tabs, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useNavigate, useParams } from 'react-router-dom'

import QueryBoundary from '../../components/QueryBoundary'
import StatusTag from '../../components/StatusTag'
import { SketchEmpty } from '../../components/sketch'
import { useUsers } from '../../hooks/useUsers'
import { projectService } from '../../services/project'
import { sampleService } from '../../services/sample'
import type { SampleTestRow } from '../../types'
import { formatDate, formatDateTime } from '../../utils/format'

const { Paragraph, Text } = Typography

function specText(row: SampleTestRow): string {
  if (row.spec_text) return row.spec_text
  const lo = row.spec_lower
  const hi = row.spec_upper
  if (lo != null && hi != null) return `${lo} ~ ${hi}`
  if (lo != null) return `≥ ${lo}`
  if (hi != null) return `≤ ${hi}`
  return '—'
}

function resultText(row: SampleTestRow): string {
  if (row.value_num != null) return `${row.value_num}${row.unit ? ` ${row.unit}` : ''}`
  if (row.value_text) return row.value_text
  return '—'
}

export default function SampleDetailPage() {
  const { id } = useParams()
  const sampleId = Number(id)
  const navigate = useNavigate()
  const { getName } = useUsers()

  const sampleQuery = useQuery({
    queryKey: ['sample', sampleId],
    queryFn: () => sampleService.getSample(sampleId),
    enabled: Number.isFinite(sampleId),
  })
  const sample = sampleQuery.data

  const projectQuery = useQuery({
    queryKey: ['project', sample?.project_id],
    queryFn: () => projectService.getProject(sample!.project_id),
    enabled: !!sample,
  })
  const testsQuery = useQuery({
    queryKey: ['sample', sampleId, 'tests'],
    queryFn: () => sampleService.listSampleTests(sampleId),
    enabled: Number.isFinite(sampleId),
  })

  const testColumns: ColumnsType<SampleTestRow> = [
    { title: '方法编号', dataIndex: 'method_code', width: 120 },
    { title: '检测项', dataIndex: 'method_name', ellipsis: true },
    { title: '规格', key: 'spec', width: 140, render: (_, row) => specText(row) },
    {
      title: '检测状态',
      dataIndex: 'status',
      width: 110,
      render: (_, row) => <StatusTag kind="test" value={row.status} />,
    },
    { title: '负责人', dataIndex: 'assigned_to', width: 100, render: (_, row) => getName(row.assigned_to ?? undefined) },
    {
      title: '结果',
      key: 'result',
      width: 130,
      render: (_, row) => {
        const oos = row.judgment === 'fail' || row.judgment === 'oos'
        return (
          <Text style={oos ? { color: 'var(--ant-color-error, #b4453c)', fontWeight: 600 } : undefined}>
            {resultText(row)}
          </Text>
        )
      },
    },
    { title: '判定', dataIndex: 'judgment', width: 100, render: (_, row) => <StatusTag kind="judgment" value={row.judgment} /> },
    {
      title: '审核',
      dataIndex: 'review_status',
      width: 90,
      render: (_, row) => <StatusTag kind="review" value={row.review_status} />,
    },
  ]

  return (
    <PageContainer
      title="样品详情"
      onBack={() => navigate('/samples')}
      extra={<Button onClick={() => navigate('/samples')}>返回列表</Button>}
    >
      <QueryBoundary
        loading={sampleQuery.isLoading}
        error={sampleQuery.error}
        onRetry={() => sampleQuery.refetch()}
        isEmpty={!sample}
        emptyText="样品不存在或已删除"
      >
        {sample ? (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Card bordered>
              <Descriptions
                column={{ xs: 1, sm: 2, lg: 3 }}
                title={
                  <Space>
                    <span>{sample.sample_code}</span>
                    <StatusTag kind="sample" value={sample.status} />
                    {sample.priority === 'urgent' ? <StatusTag kind="batch" value="low" /> : null}
                  </Space>
                }
              >
                <Descriptions.Item label="样品名称">{sample.name}</Descriptions.Item>
                <Descriptions.Item label="化合物">{sample.compound_name}</Descriptions.Item>
                <Descriptions.Item label="所属项目">
                  {projectQuery.data
                    ? `${projectQuery.data.project_code} · ${projectQuery.data.name}`
                    : `#${sample.project_id}`}
                </Descriptions.Item>
                <Descriptions.Item label="样品类型">{sample.sample_type ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="批号">{sample.batch_no ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="来源">{sample.source ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="收样时间">{formatDateTime(sample.received_at)}</Descriptions.Item>
                <Descriptions.Item label="截止日期">{formatDate(sample.due_date)}</Descriptions.Item>
                <Descriptions.Item label="最近更新">
                  {formatDateTime(sample.updated_at ?? sample.created_at)}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Card bordered>
              <Tabs
                items={[
                  {
                    key: 'info',
                    label: '基本信息',
                    children: (
                      <Descriptions column={{ xs: 1, sm: 2 }} bordered size="small">
                        <Descriptions.Item label="结构 SMILES" span={2}>
                          {sample.structure_smiles ? (
                            <Paragraph copyable style={{ marginBottom: 0 }}>
                              {sample.structure_smiles}
                            </Paragraph>
                          ) : (
                            '—'
                          )}
                        </Descriptions.Item>
                        <Descriptions.Item label="备注" span={2}>
                          {sample.notes ?? '—'}
                        </Descriptions.Item>
                      </Descriptions>
                    ),
                  },
                  {
                    key: 'tests',
                    label: `检测项与结果（${testsQuery.data?.length ?? 0}）`,
                    children: (
                      <Table<SampleTestRow>
                        rowKey="id"
                        size="small"
                        columns={testColumns}
                        dataSource={testsQuery.data ?? []}
                        loading={testsQuery.isLoading}
                        pagination={false}
                        scroll={{ x: 900 }}
                        locale={{ emptyText: <SketchEmpty description="该样品暂无检测项" /> }}
                      />
                    ),
                  },
                ]}
              />
            </Card>
          </Space>
        ) : null}
      </QueryBoundary>
    </PageContainer>
  )
}
