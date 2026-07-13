import { ImportOutlined, PlusOutlined } from '@ant-design/icons'
import {
  PageContainer,
  ProTable,
  type ActionType,
  type ProColumns,
} from '@ant-design/pro-components'
import { Alert, App, Button, Popconfirm } from 'antd'
import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import type { ApiError } from '../../api/errors'
import { USE_MOCK } from '../../api/runtime'
import { useAuth } from '../../auth/useAuth'
import { canImportInventory, canManageInventory } from '../../auth/permissions'
import StatusTag from '../../components/StatusTag'
import { SketchEmpty } from '../../components/sketch'
import { CATEGORY_OPTIONS, categoryLabel } from '../../components/status'
import { inventoryService } from '../../services/inventory'
import type { BatchStatus, InventoryRow, MaterialCategory } from '../../types'
import { formatDate } from '../../utils/format'
import { AdjustModal, InboundModal, NewBatchModal } from './InventoryModals'
import ReagentImportModal from './ReagentImportModal'

interface InventoryParams {
  material_code?: string
  material_name?: string
  cas_no?: string
  category?: MaterialCategory
  batch_no?: string
  supplier?: string
  location?: string
  status?: BatchStatus
}

const STATUS_OPTIONS = [
  { label: '正常', value: 'normal' },
  { label: '低库存', value: 'low' },
  { label: '已用尽', value: 'depleted' },
  { label: '过期', value: 'expired' },
  { label: '冻结', value: 'frozen' },
]

export default function InventoryListPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const { message } = App.useApp()
  const actionRef = useRef<ActionType>(null)
  const [loadError, setLoadError] = useState<string>()
  const [importOpen, setImportOpen] = useState(false)

  if (!user) return null
  const canManage = canManageInventory(user.role)
  const canImport = canImportInventory(user.role)

  const handleFreeze = async (row: InventoryRow) => {
    try {
      await inventoryService.setFrozen(row.batch_id, row.status !== 'frozen', user.id)
      message.success(row.status !== 'frozen' ? '已冻结' : '已解冻')
      actionRef.current?.reload()
    } catch (error) {
      message.error((error as ApiError).message || '操作失败')
    }
  }

  const columns: ProColumns<InventoryRow>[] = [
    { title: '物料编号', dataIndex: 'material_code', width: 120, fixed: 'left', copyable: true },
    { title: '物料名称', dataIndex: 'material_name', ellipsis: true },
    {
      title: '类别',
      dataIndex: 'category',
      width: 100,
      valueType: 'select',
      fieldProps: { options: CATEGORY_OPTIONS, allowClear: true },
      render: (_, r) => categoryLabel[r.category] ?? r.category,
    },
    { title: 'CAS号', dataIndex: 'cas_no', width: 110, render: (_, r) => r.cas_no ?? '—' },
    { title: '批号', dataIndex: 'batch_no', width: 130 },
    { title: '当前库存', dataIndex: 'quantity', width: 90, search: false, render: (_, r) => `${r.quantity}` },
    { title: '单位', dataIndex: 'unit', width: 70, search: false },
    { title: '供应商', dataIndex: 'supplier', width: 110, render: (_, r) => r.supplier ?? '—' },
    { title: '库位', dataIndex: 'location', width: 110, render: (_, r) => r.location ?? '—' },
    { title: '有效期', dataIndex: 'expiry_date', width: 110, search: false, render: (_, r) => formatDate(r.expiry_date) },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      valueType: 'select',
      fieldProps: { options: STATUS_OPTIONS, allowClear: true },
      render: (_, r) => <StatusTag kind="batch" value={r.status} />,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 200,
      fixed: 'right',
      render: (_, row) => [
        <a key="view" onClick={() => navigate(`/inventory/${row.batch_id}`)}>
          查看
        </a>,
        canManage ? (
          <InboundModal key="in" batchId={row.batch_id} actorId={user.id} trigger={<a>入库</a>} onSaved={() => actionRef.current?.reload()} />
        ) : null,
        canManage ? (
          <AdjustModal key="adj" batchId={row.batch_id} actorId={user.id} trigger={<a>调整</a>} onSaved={() => actionRef.current?.reload()} />
        ) : null,
        USE_MOCK && canManage ? (
          <Popconfirm key="frz" title={row.status === 'frozen' ? '确认解冻？' : '确认冻结？'} onConfirm={() => handleFreeze(row)} okText="确定" cancelText="取消">
            <a>{row.status === 'frozen' ? '解冻' : '冻结'}</a>
          </Popconfirm>
        ) : null,
      ],
    },
  ]

  return (
    <PageContainer title="试剂库存">
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
      <ProTable<InventoryRow, InventoryParams>
        actionRef={actionRef}
        rowKey="batch_id"
        columns={columns}
        scroll={{ x: 1300 }}
        cardBordered
        locale={{ emptyText: <SketchEmpty description="暂无试剂库存" /> }}
        options={{ density: true, reload: true, setting: true }}
        pagination={{ defaultPageSize: 10, showSizeChanger: true }}
        search={{ labelWidth: 'auto' }}
        rowClassName={(r) => (r.status === 'expired' || r.status === 'low' ? 'lims-row-warning' : '')}
        request={async (params) => {
          try {
            setLoadError(undefined)
            const res = await inventoryService.listInventory({
              page: params.current,
              page_size: params.pageSize,
              material_code: params.material_code,
              material_name: params.material_name,
              cas_no: params.cas_no,
              category: params.category,
              batch_no: params.batch_no,
              supplier: params.supplier,
              location: params.location,
              status: params.status,
            })
            return { data: res.items, total: res.total, success: true }
          } catch (error) {
            setLoadError((error as { message?: string }).message ?? '库存列表加载失败')
            return { data: [], total: 0, success: false }
          }
        }}
        toolBarRender={() =>
          canImport || (USE_MOCK && canManage)
            ? [
                !USE_MOCK && canImport ? (
                  <Button key="import" icon={<ImportOutlined />} onClick={() => setImportOpen(true)}>
                    导入库存
                  </Button>
                ) : null,
                USE_MOCK && canManage ? (
                  <NewBatchModal
                    key="new"
                    actorId={user.id}
                    trigger={
                      <Button type="primary" icon={<PlusOutlined />}>
                        新增物料/批次
                      </Button>
                    }
                    onSaved={() => actionRef.current?.reload()}
                  />
                ) : null,
              ]
            : []
        }
      />
      <ReagentImportModal
        open={importOpen}
        onCancel={() => setImportOpen(false)}
        onImported={() => actionRef.current?.reload()}
      />
    </PageContainer>
  )
}
