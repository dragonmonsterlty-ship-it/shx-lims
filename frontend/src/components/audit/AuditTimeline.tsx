import { useQuery } from '@tanstack/react-query'
import { Alert, Button, Card, Skeleton, Space, Tag, Timeline, Typography } from 'antd'
import type { ReactNode } from 'react'

import { getEntityAuditTimeline } from '../../services/audit'
import { formatDateTime } from '../../utils/format'
import { SketchEmpty } from '../sketch'

const ACTION_LABELS: Record<string, string> = {
  create: '创建',
  update: '更新',
  delete: '删除',
  submit: '提交',
  approve: '批准',
  reject: '退回',
  archive: '归档',
  upload: '上传',
  download: '下载',
  enable_user: '启用用户',
  disable_user: '禁用用户',
  change_role: '修改角色',
  reset_password: '重置密码',
}

export interface AuditTimelineProps {
  entityType: string
  entityId: number
  title?: ReactNode
  compact?: boolean
}

export default function AuditTimeline({
  entityType,
  entityId,
  title = '审计时间线',
  compact = false,
}: AuditTimelineProps) {
  const query = useQuery({
    queryKey: ['audit-timeline', entityType, entityId],
    queryFn: () => getEntityAuditTimeline(entityType, entityId),
    enabled: Number.isFinite(entityId),
  })

  let content: ReactNode
  if (query.isLoading) {
    content = <Skeleton active paragraph={{ rows: compact ? 2 : 3 }} />
  } else if (query.error) {
    content = (
      <Alert
        type="error"
        showIcon
        message="审计时间线加载失败"
        description={(query.error as { message?: string }).message ?? '请稍后重试'}
        action={
          <Button size="small" onClick={() => query.refetch()}>
            重新加载
          </Button>
        }
      />
    )
  } else if (!query.data?.length) {
    content = <SketchEmpty description="暂无审计记录" size={compact ? 72 : 96} />
  } else {
    content = (
      <Timeline
        items={query.data.map((log) => ({
          children: (
            <Space direction="vertical" size={2}>
              <Space wrap>
                <Tag>{ACTION_LABELS[log.action] ?? log.action}</Tag>
                <Typography.Text>
                  {log.actor_user_id == null ? '系统' : `用户 #${log.actor_user_id}`}
                </Typography.Text>
                {log.actor_role ? (
                  <Typography.Text type="secondary">{log.actor_role}</Typography.Text>
                ) : null}
              </Space>
              <Typography.Text type="secondary">{formatDateTime(log.created_at)}</Typography.Text>
            </Space>
          ),
        }))}
      />
    )
  }

  if (compact) {
    return (
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        {title ? <Typography.Text strong>{title}</Typography.Text> : null}
        {content}
      </Space>
    )
  }

  return (
    <Card title={title} size="small">
      {content}
    </Card>
  )
}
