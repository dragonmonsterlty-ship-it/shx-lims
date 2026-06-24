import { PageContainer } from '@ant-design/pro-components'
import { useQuery } from '@tanstack/react-query'
import { Alert, Descriptions, Empty, Space, Table, Tabs, Tag } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'

import { useAuth } from '../../auth/useAuth'
import { USE_MOCK } from '../../api/runtime'
import { canManageInventory } from '../../auth/permissions'
import QueryBoundary from '../../components/QueryBoundary'
import StatusTag from '../../components/StatusTag'
import { categoryLabel } from '../../components/status'
import { useUsers } from '../../hooks/useUsers'
import { inventoryService } from '../../services/inventory'
import type { Id, InventoryTransaction } from '../../types'
import { formatDate, formatDateTime } from '../../utils/format'
import { AdjustModal, InboundModal } from './InventoryModals'

const TXN_TYPE_LABEL: Record<string, string> = {
  inbound: '入库',
  outbound: '出库',
  adjustment: '调整',
  return: '退库',
}

export default function InventoryDetailPage() {
  const { id } = useParams()
  const batchId = Number(id)
  const { user } = useAuth()
  const navigate = useNavigate()
  const { getName } = useUsers()

  const batchQuery = useQuery({
    queryKey: ['inventory', 'batch', batchId],
    queryFn: () => inventoryService.getBatch(batchId),
    enabled: Number.isFinite(batchId),
  })
  const txnQuery = useQuery({
    queryKey: ['inventory', 'batch', batchId, 'txns'],
    queryFn: () => inventoryService.listTransactions(batchId),
    enabled: Number.isFinite(batchId),
  })
  const expQuery = useQuery({
    queryKey: ['inventory', 'batch', batchId, 'experiments'],
    queryFn: () => inventoryService.listBatchExperiments(batchId),
    enabled: Number.isFinite(batchId),
  })

  const batch = batchQuery.data?.batch
  const material = batchQuery.data?.material
  const canManage = !!user && canManageInventory(user.role)

  const refetch = () => {
    batchQuery.refetch()
    txnQuery.refetch()
  }

  const txnColumns = [
    { title: '时间', dataIndex: 'at', width: 160, render: (v: string) => formatDateTime(v) },
    {
      title: '类型',
      dataIndex: 'transaction_type',
      width: 90,
      render: (v: string) => TXN_TYPE_LABEL[v] ?? v,
    },
    {
      title: '变动量',
      dataIndex: 'qty_delta',
      width: 100,
      render: (v: number, r: InventoryTransaction) => (
        <span style={{ color: v < 0 ? '#b4453c' : '#3e7c5a' }}>
          {v > 0 ? `+${v}` : v} {r.unit}
        </span>
      ),
    },
    {
      title: '来源',
      dataIndex: 'source_type',
      width: 140,
      render: (v: string, r: InventoryTransaction) =>
        v === 'experiment' ? `实验 #${r.source_id ?? ''}` : '手动',
    },
    { title: '操作人', dataIndex: 'actor_id', width: 100, render: (v: Id | null) => getName(v) },
    { title: '原因', dataIndex: 'reason', render: (v: string | null) => v ?? '—' },
  ]

  const expColumns = [
    {
      title: '实验编号',
      dataIndex: 'experiment_no',
      width: 130,
      render: (v: string, r: { experiment_id: Id }) => (
        <a onClick={() => navigate(`/experiments/${r.experiment_id}`)}>{v}</a>
      ),
    },
    { title: '实验标题', dataIndex: 'title', ellipsis: true },
    {
      title: '项目',
      dataIndex: 'project_name',
      width: 170,
      render: (_: unknown, r: { project_code: string; project_name: string }) =>
        r.project_name ? `${r.project_code} · ${r.project_name}` : '—',
    },
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
      title={batch ? `${material?.name ?? ''} · ${batch.batch_no}` : '库存批次详情'}
      onBack={() => navigate('/inventory')}
      tags={batch ? <StatusTag kind="batch" value={batch.status} /> : undefined}
      extra={
        batch && canManage ? (
          <Space>
            <InboundModal batchId={batch.id} actorId={user.id} trigger={<a>入库</a>} onSaved={refetch} />
            <AdjustModal batchId={batch.id} actorId={user.id} trigger={<a>调整</a>} onSaved={refetch} />
          </Space>
        ) : undefined
      }
    >
      <QueryBoundary loading={batchQuery.isLoading} error={batchQuery.error} onRetry={() => batchQuery.refetch()}>
        {batch ? (
          <Tabs
            items={[
              {
                key: 'basic',
                label: '基础信息',
                children: (
                  <Descriptions bordered column={2} size="small">
                    <Descriptions.Item label="物料编号">{material?.material_code ?? '—'}</Descriptions.Item>
                    <Descriptions.Item label="物料名称">{material?.name ?? '—'}</Descriptions.Item>
                    <Descriptions.Item label="类别">{material ? categoryLabel[material.category] : '—'}</Descriptions.Item>
                    <Descriptions.Item label="CAS号">{material?.cas_no ?? '—'}</Descriptions.Item>
                    <Descriptions.Item label="批号">{batch.batch_no}</Descriptions.Item>
                    <Descriptions.Item label="供应商">{batch.supplier ?? '—'}</Descriptions.Item>
                    <Descriptions.Item label="纯度/规格">{batch.purity ?? material?.specification ?? '—'}</Descriptions.Item>
                    <Descriptions.Item label="库位">{batch.location ?? '—'}</Descriptions.Item>
                    <Descriptions.Item label="当前库存">
                      {batch.quantity} {batch.unit}
                    </Descriptions.Item>
                    <Descriptions.Item label="状态">
                      <StatusTag kind="batch" value={batch.status} />
                    </Descriptions.Item>
                    <Descriptions.Item label="到货/有效期">
                      {formatDate(batch.received_date)} ~ {formatDate(batch.expiry_date)}
                    </Descriptions.Item>
                    <Descriptions.Item label="储存条件">{material?.storage_condition ?? '—'}</Descriptions.Item>
                  </Descriptions>
                ),
              },
              {
                key: 'txns',
                label: '库存流水',
                children: (
                  <Table<InventoryTransaction>
                    rowKey="id"
                    size="small"
                    loading={txnQuery.isLoading}
                    dataSource={txnQuery.data ?? []}
                    columns={txnColumns}
                    pagination={false}
                    locale={{ emptyText: '暂无流水' }}
                  />
                ),
              },
              {
                key: 'experiments',
                label: '关联实验',
                children: (
                  <Table
                    rowKey="experiment_id"
                    size="small"
                    loading={expQuery.isLoading}
                    dataSource={expQuery.data ?? []}
                    columns={expColumns}
                    pagination={false}
                    locale={{ emptyText: '暂无关联实验' }}
                  />
                ),
              },
              {
                key: 'remark',
                label: '备注/附件',
                children: (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Descriptions bordered column={1} size="small">
                      <Descriptions.Item label="备注">{batch.remark || '—'}</Descriptions.Item>
                      <Descriptions.Item label="管制标识">
                        {material?.safety_level === '管制' ? <Tag color="red">管制品</Tag> : '—'}
                      </Descriptions.Item>
                    </Descriptions>
                    <Alert
                      type="info"
                      showIcon
                      message={
                        USE_MOCK
                          ? '附件为占位，暂不支持上传/扫码/条码打印。'
                          : '当前后端库存契约不包含附件、扫码或条码打印接口。'
                      }
                    />
                    <Empty description="暂无附件" />
                  </Space>
                ),
              },
            ]}
          />
        ) : null}
      </QueryBoundary>
    </PageContainer>
  )
}
