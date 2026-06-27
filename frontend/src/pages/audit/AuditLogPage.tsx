import { PageContainer, ProTable, type ProColumns } from '@ant-design/pro-components'
import { Alert, Button, Descriptions, Modal, Tag, Typography } from 'antd'
import { useState } from 'react'

import { SketchEmpty } from '../../components/sketch'
import { listAuditLogs } from '../../services/audit'
import type { AuditLog, AuditLogListQuery } from '../../types'
import { formatDateTime } from '../../utils/format'
import { formatAuditJson, summarizeAuditJson } from './auditView'

interface AuditSearchParams {
  entity_type?: string
  entity_id?: number
  project_id?: number
  actor_user_id?: number
  action?: string
  date_range?: [string, string]
}

const ENTITY_OPTIONS = [
  'experiment',
  'daily_report',
  'sample',
  'test_task',
  'test_result',
  'attachment',
  'user',
].map((value) => ({ label: value, value }))

const ACTION_OPTIONS = [
  'create',
  'update',
  'delete',
  'submit',
  'approve',
  'reject',
  'archive',
  'upload',
  'download',
  'enable_user',
  'disable_user',
  'change_role',
  'reset_password',
].map((value) => ({ label: value, value }))

function JsonBlock({ value }: { value: unknown }) {
  return (
    <Typography.Paragraph>
      <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
        {formatAuditJson(value)}
      </pre>
    </Typography.Paragraph>
  )
}

export default function AuditLogPage() {
  const [loadError, setLoadError] = useState<string>()
  const [selected, setSelected] = useState<AuditLog | null>(null)

  const columns: ProColumns<AuditLog>[] = [
    {
      title: '时间',
      dataIndex: 'created_at',
      width: 170,
      search: false,
      renderText: (value) => formatDateTime(value),
    },
    {
      title: '时间范围',
      dataIndex: 'date_range',
      valueType: 'dateTimeRange',
      hideInTable: true,
    },
    { title: '操作者 ID', dataIndex: 'actor_user_id', width: 110 },
    {
      title: '操作者角色',
      dataIndex: 'actor_role',
      width: 130,
      search: false,
      renderText: (value) => value || '—',
    },
    {
      title: '动作',
      dataIndex: 'action',
      width: 130,
      valueType: 'select',
      fieldProps: { options: ACTION_OPTIONS, allowClear: true },
      render: (_, row) => <Tag>{row.action}</Tag>,
    },
    {
      title: '实体类型',
      dataIndex: 'entity_type',
      width: 140,
      valueType: 'select',
      fieldProps: { options: ENTITY_OPTIONS, allowClear: true },
    },
    { title: '实体 ID', dataIndex: 'entity_id', width: 100 },
    { title: '项目 ID', dataIndex: 'project_id', width: 100 },
    { title: '目标用户 ID', dataIndex: 'target_user_id', width: 120, search: false },
    {
      title: '变更摘要',
      key: 'change_summary',
      width: 260,
      search: false,
      ellipsis: true,
      render: (_, row) =>
        `前：${summarizeAuditJson(row.before_data)}；后：${summarizeAuditJson(row.after_data)}`,
    },
    {
      title: '元数据',
      dataIndex: 'metadata',
      width: 180,
      search: false,
      ellipsis: true,
      renderText: (value) => summarizeAuditJson(value),
    },
    {
      title: '操作',
      valueType: 'option',
      width: 90,
      fixed: 'right',
      render: (_, row) => (
        <Button type="link" size="small" onClick={() => setSelected(row)}>
          查看详情
        </Button>
      ),
    },
  ]

  return (
    <PageContainer title="审计日志">
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

      <ProTable<AuditLog, AuditSearchParams>
        rowKey="id"
        columns={columns}
        scroll={{ x: 1550 }}
        search={{ labelWidth: 'auto' }}
        options={{ density: true, reload: true, setting: true }}
        pagination={{ defaultPageSize: 20, showSizeChanger: true }}
        locale={{ emptyText: <SketchEmpty description="暂无审计日志" /> }}
        request={async (params) => {
          const [date_from, date_to] = params.date_range ?? []
          const query: AuditLogListQuery = {
            entity_type: params.entity_type,
            entity_id: params.entity_id,
            project_id: params.project_id,
            actor_user_id: params.actor_user_id,
            action: params.action,
            date_from,
            date_to,
            page: params.current,
            page_size: params.pageSize,
          }
          try {
            setLoadError(undefined)
            const result = await listAuditLogs(query)
            return { data: result.items, total: result.total, success: true }
          } catch (error) {
            setLoadError((error as { message?: string }).message ?? '审计日志加载失败')
            return { data: [], total: 0, success: false }
          }
        }}
      />

      <Modal
        title="审计日志详情"
        open={!!selected}
        width={760}
        footer={null}
        onCancel={() => setSelected(null)}
      >
        {selected ? (
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="日志 ID">{selected.id}</Descriptions.Item>
            <Descriptions.Item label="时间">{formatDateTime(selected.created_at)}</Descriptions.Item>
            <Descriptions.Item label="操作者">
              {selected.actor_user_id ?? '—'} / {selected.actor_role ?? '—'}
            </Descriptions.Item>
            <Descriptions.Item label="动作">{selected.action}</Descriptions.Item>
            <Descriptions.Item label="实体">
              {selected.entity_type} #{selected.entity_id}
            </Descriptions.Item>
            <Descriptions.Item label="项目 ID">{selected.project_id ?? '—'}</Descriptions.Item>
            <Descriptions.Item label="目标用户 ID" span={2}>
              {selected.target_user_id ?? '—'}
            </Descriptions.Item>
            <Descriptions.Item label="变更前" span={2}>
              <JsonBlock value={selected.before_data} />
            </Descriptions.Item>
            <Descriptions.Item label="变更后" span={2}>
              <JsonBlock value={selected.after_data} />
            </Descriptions.Item>
            <Descriptions.Item label="元数据" span={2}>
              <JsonBlock value={selected.metadata} />
            </Descriptions.Item>
          </Descriptions>
        ) : null}
      </Modal>
    </PageContainer>
  )
}
