import { PageContainer, ProTable, type ProColumns } from '@ant-design/pro-components'

import { SketchEmpty } from '../../components/sketch'

/**
 * 对照品台账（M1 占位版）：仅空状态骨架，业务列与入库/领用留待 M2/M3。
 * 列定义先按契约占位，空状态用统一 SketchEmpty（列表空状态属视觉宪法白名单）。
 */
interface RefStandardRow {
  id: number
  code: string
  name: string
  batch_no: string | null
  current_amount: number | null
  unit: string | null
  expires_at: string | null
  status: string
}

const columns: ProColumns<RefStandardRow>[] = [
  { title: '编号', dataIndex: 'code', width: 160 },
  { title: '名称', dataIndex: 'name', ellipsis: true },
  { title: '批号', dataIndex: 'batch_no', width: 140 },
  { title: '余量', dataIndex: 'current_amount', width: 120 },
  { title: '效期', dataIndex: 'expires_at', width: 140 },
  { title: '状态', dataIndex: 'status', width: 120 },
]

export default function RefStandardListPage() {
  return (
    <PageContainer title="对照品台账">
      <ProTable<RefStandardRow>
        rowKey="id"
        columns={columns}
        search={false}
        pagination={false}
        options={{ density: true, reload: true, setting: true }}
        locale={{ emptyText: <SketchEmpty description="暂无对照品" /> }}
        request={async () => ({ data: [], success: true, total: 0 })}
      />
    </PageContainer>
  )
}
