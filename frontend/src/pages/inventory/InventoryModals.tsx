import {
  ModalForm,
  ProFormDatePicker,
  ProFormDependency,
  ProFormDigit,
  ProFormSelect,
  ProFormText,
} from '@ant-design/pro-components'
import { App } from 'antd'
import dayjs from 'dayjs'
import type { ReactNode } from 'react'

import type { ApiError } from '../../api/errors'
import { CATEGORY_OPTIONS } from '../../components/status'
import { inventoryService } from '../../services/inventory'
import type { Id, MaterialCategory } from '../../types'

const fmtDate = (v?: string | dayjs.Dayjs | null) => (v ? dayjs(v).format('YYYY-MM-DD') : null)

/** 新增物料/批次（可选已有物料或新建物料）。 */
export function NewBatchModal({ actorId, trigger, onSaved }: { actorId: Id; trigger: ReactNode; onSaved?: () => void }) {
  const { message } = App.useApp()
  return (
    <ModalForm
      title="新增物料/批次"
      trigger={<span>{trigger}</span>}
      width={560}
      modalProps={{ destroyOnHidden: true }}
      onFinish={async (v: {
        material_id?: Id
        material_code?: string
        name?: string
        category?: MaterialCategory
        cas_no?: string
        specification?: string
        unit: string
        safety_level?: string
        storage_condition?: string
        batch_no: string
        supplier?: string
        purity?: string
        location?: string
        quantity: number
        received_date?: string | dayjs.Dayjs
        expiry_date?: string | dayjs.Dayjs
        remark?: string
      }) => {
        try {
          await inventoryService.createBatch(
            {
              material_id: v.material_id,
              material_code: v.material_code,
              name: v.name,
              category: v.category,
              cas_no: v.cas_no ?? null,
              specification: v.specification ?? null,
              unit: v.unit,
              safety_level: v.safety_level ?? null,
              storage_condition: v.storage_condition ?? null,
              batch_no: v.batch_no,
              supplier: v.supplier ?? null,
              purity: v.purity ?? null,
              location: v.location ?? null,
              quantity: v.quantity,
              received_date: fmtDate(v.received_date),
              expiry_date: fmtDate(v.expiry_date),
              remark: v.remark ?? null,
            },
            actorId,
          )
          message.success('批次已创建并入库')
          onSaved?.()
          return true
        } catch (error) {
          message.error((error as ApiError).message || '创建失败')
          return false
        }
      }}
    >
      <ProFormSelect
        name="material_id"
        label="已有物料"
        request={async () => {
          const materials = await inventoryService.listMaterials()
          return materials.map((m) => ({ label: `${m.material_code} · ${m.name}`, value: m.id }))
        }}
        fieldProps={{ showSearch: true, optionFilterProp: 'label', allowClear: true }}
        tooltip="选择已有物料；留空则在下方新建物料"
      />
      <ProFormDependency name={['material_id']}>
        {({ material_id }) =>
          material_id ? null : (
            <>
              <ProFormText name="material_code" label="物料编号" rules={[{ required: true }]} />
              <ProFormText name="name" label="物料名称" rules={[{ required: true }]} />
              <ProFormSelect name="category" label="类别" options={CATEGORY_OPTIONS} rules={[{ required: true }]} />
              <ProFormText name="cas_no" label="CAS 号" />
              <ProFormText name="specification" label="规格" />
              <ProFormText name="safety_level" label="安全等级" />
              <ProFormText name="storage_condition" label="储存条件" />
            </>
          )
        }
      </ProFormDependency>
      <ProFormText name="batch_no" label="批号" rules={[{ required: true }]} />
      <ProFormText name="unit" label="单位" rules={[{ required: true }]} />
      <ProFormDigit name="quantity" label="入库数量" min={0} rules={[{ required: true }]} />
      <ProFormText name="supplier" label="供应商" />
      <ProFormText name="purity" label="纯度" />
      <ProFormText name="location" label="库位" />
      <ProFormDatePicker name="received_date" label="到货日期" />
      <ProFormDatePicker name="expiry_date" label="有效期" />
      <ProFormText name="remark" label="备注" />
    </ModalForm>
  )
}

/** 手动入库。 */
export function InboundModal({ batchId, actorId, trigger, onSaved }: { batchId: Id; actorId: Id; trigger: ReactNode; onSaved?: () => void }) {
  const { message } = App.useApp()
  return (
    <ModalForm
      title="手动入库"
      trigger={<span>{trigger}</span>}
      width={420}
      modalProps={{ destroyOnHidden: true }}
      onFinish={async (v: { qty: number; reason?: string }) => {
        try {
          await inventoryService.inbound({ batch_id: batchId, qty: v.qty, reason: v.reason ?? null }, actorId)
          message.success('入库成功')
          onSaved?.()
          return true
        } catch (error) {
          message.error((error as ApiError).message || '入库失败')
          return false
        }
      }}
    >
      <ProFormDigit name="qty" label="入库数量" min={0.0001} rules={[{ required: true }]} />
      <ProFormText name="reason" label="原因/单号" />
    </ModalForm>
  )
}

/** 手动调整（正负皆可）。 */
export function AdjustModal({ batchId, actorId, trigger, onSaved }: { batchId: Id; actorId: Id; trigger: ReactNode; onSaved?: () => void }) {
  const { message } = App.useApp()
  return (
    <ModalForm
      title="库存调整"
      trigger={<span>{trigger}</span>}
      width={420}
      modalProps={{ destroyOnHidden: true }}
      onFinish={async (v: { qty_delta: number; reason?: string }) => {
        try {
          await inventoryService.adjust({ batch_id: batchId, qty_delta: v.qty_delta, reason: v.reason ?? null }, actorId)
          message.success('调整成功')
          onSaved?.()
          return true
        } catch (error) {
          message.error((error as ApiError).message || '调整失败')
          return false
        }
      }}
    >
      <ProFormDigit name="qty_delta" label="调整量（正增负减）" rules={[{ required: true }]} />
      <ProFormText name="reason" label="原因" rules={[{ required: true, message: '请填写调整原因' }]} />
    </ModalForm>
  )
}
