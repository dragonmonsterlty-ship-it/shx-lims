import { PageContainer } from '@ant-design/pro-components'
import { useQuery } from '@tanstack/react-query'
import { Card, Col, List, Row, Statistic, Typography } from 'antd'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '../../auth/useAuth'
import StatusTag from '../../components/StatusTag'
import { useUsers } from '../../hooks/useUsers'
import { dailyReportService } from '../../services/dailyReport'
import { experimentService } from '../../services/experiment'
import { inventoryService } from '../../services/inventory'
import { projectService } from '../../services/project'
import { formatDate } from '../../utils/format'

const { Text } = Typography

export default function DashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const { getName } = useUsers()

  const projectsQ = useQuery({
    queryKey: ['dashboard', 'projects', user?.id],
    queryFn: () => projectService.listProjects({ page_size: 500 }, user!),
    enabled: !!user,
  })
  const expQ = useQuery({
    queryKey: ['dashboard', 'experiments', user?.id],
    queryFn: () => experimentService.listExperiments({ page_size: 500 }, user!),
    enabled: !!user,
  })
  const repQ = useQuery({
    queryKey: ['dashboard', 'reports', user?.id],
    queryFn: () => dailyReportService.listReports({ page_size: 500 }, user!),
    enabled: !!user,
  })
  const invQ = useQuery({
    queryKey: ['dashboard', 'inventory'],
    queryFn: () => inventoryService.listInventory({ page_size: 500 }),
  })

  if (!user) return null

  const projItems = projectsQ.data?.items ?? []
  const expItems = expQ.data?.items ?? []
  const repItems = repQ.data?.items ?? []
  const invItems = invQ.data?.items ?? []

  const projActive = projItems.filter((p) => p.status === 'active').length
  const expActive = expItems.filter((e) => e.status === 'in_progress').length
  const reportPending = repItems.filter((r) => r.status === 'submitted').length
  const warnBatches = invItems.filter(
    (b) => b.status === 'low' || b.status === 'depleted' || b.status === 'expired',
  )

  const cards = [
    {
      title: '进行中 / 项目总数',
      value: projActive,
      suffix: `/ ${projectsQ.data?.total ?? 0}`,
      loading: projectsQ.isLoading,
      to: '/projects',
    },
    {
      title: '进行中 / 实验总数',
      value: expActive,
      suffix: `/ ${expQ.data?.total ?? 0}`,
      loading: expQ.isLoading,
      to: '/experiments',
    },
    { title: '待确认日报', value: reportPending, suffix: '', loading: repQ.isLoading, to: '/daily-reports' },
    {
      title: '低库存/已用尽批次',
      value: warnBatches.length,
      suffix: '',
      loading: invQ.isLoading,
      to: '/inventory',
    },
  ]

  const recentExps = expItems.slice(0, 6)
  const recentReports = repItems.slice(0, 6)

  return (
    <PageContainer title="仪表盘" content={`欢迎，${user.full_name}`}>
      <Row gutter={[16, 16]}>
        {cards.map((c) => (
          <Col key={c.title} xs={12} sm={12} md={6} lg={6} xl={6}>
            <Card hoverable size="small" onClick={() => navigate(c.to)} style={{ borderColor: 'var(--line)' }}>
              <Statistic title={c.title} value={c.value} suffix={c.suffix} loading={c.loading} />
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="近期实验" size="small" style={{ borderColor: 'var(--line)' }}>
            <List
              loading={expQ.isLoading}
              dataSource={recentExps}
              locale={{ emptyText: '暂无实验' }}
              renderItem={(e) => (
                <List.Item
                  style={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/experiments/${e.id}`)}
                  actions={[<StatusTag key="s" kind="experiment" value={e.status} />]}
                >
                  <List.Item.Meta
                    title={`${e.experiment_no} · ${e.title}`}
                    description={<Text type="secondary">负责人 {getName(e.lead_user_id)}</Text>}
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="近期日报" size="small" style={{ borderColor: 'var(--line)' }}>
            <List
              loading={repQ.isLoading}
              dataSource={recentReports}
              locale={{ emptyText: '暂无日报' }}
              renderItem={(r) => (
                <List.Item
                  style={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/daily-reports/${r.id}`)}
                  actions={[<StatusTag key="s" kind="daily_report" value={r.status} />]}
                >
                  <List.Item.Meta
                    title={`${formatDate(r.report_date)} · ${getName(r.user_id)}`}
                    description={<Text ellipsis>{r.work_content}</Text>}
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24}>
          <Card
            title="库存预警"
            size="small"
            style={{ borderColor: 'var(--line)' }}
            extra={<Text type="secondary">低库存 / 已用尽 / 过期批次（阈值系统 T1.1+）</Text>}
          >
            <List
              loading={invQ.isLoading}
              dataSource={warnBatches.slice(0, 8)}
              locale={{ emptyText: '库存正常' }}
              renderItem={(b) => (
                <List.Item
                  style={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/inventory/${b.batch_id}`)}
                  actions={[
                    <StatusTag key="st" kind="batch" value={b.status} />,
                    <Text key="q" type="warning">
                      余 {b.quantity} {b.unit}
                    </Text>,
                  ]}
                >
                  <List.Item.Meta title={`${b.material_name} · ${b.batch_no}`} description={b.location ?? ''} />
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </PageContainer>
  )
}
