import {
  ModalForm,
  ProFormDatePicker,
  ProFormList,
  ProFormSelect,
  ProFormText,
  ProFormTextArea,
  type ProFormInstance,
} from '@ant-design/pro-components'
import { Alert, App } from 'antd'
import dayjs from 'dayjs'
import { useRef, type ReactNode } from 'react'

import type { ApiError } from '../../api/errors'
import { dailyReportService } from '../../services/dailyReport'
import { experimentService } from '../../services/experiment'
import { projectService } from '../../services/project'
import type { DailyReport, DailyReportInput, DailyReportItemInput, User } from '../../types'

interface DailyReportFormModalProps {
  mode: 'create' | 'edit'
  currentUser: User
  report?: DailyReport
  trigger: ReactNode
  onSaved?: () => void
}

interface FormValues {
  report_date: string
  items: DailyReportItemInput[]
}

export default function DailyReportFormModal({
  mode,
  currentUser,
  report,
  trigger,
  onSaved,
}: DailyReportFormModalProps) {
  const { message } = App.useApp()
  const isEdit = mode === 'edit'
  const formRef = useRef<ProFormInstance>(null)

  const initialValues: FormValues =
    isEdit && report
      ? {
          report_date: report.report_date,
          items:
            report.items?.map((item) => ({
              project_id: item.project_id,
              experiment_record_id: item.experiment_record_id,
              work_type: item.work_type,
              content: item.content,
              problem_note: item.problem_note,
              next_step: item.next_step,
              sort_order: item.sort_order,
            })) ?? [],
        }
      : {
          report_date: dayjs().format('YYYY-MM-DD'),
          items: [{ work_type: 'other', content: '', sort_order: 0 }],
        }

  const projectOptions = async () => {
    const res = await projectService.listProjects({ page_size: 200 }, currentUser)
    return res.items.map((p) => ({ label: `${p.project_code} · ${p.name}`, value: p.id }))
  }

  const experimentOptions = async () => {
    const res = await experimentService.listExperiments({ page_size: 200 }, currentUser)
    return res.items.map((e) => ({ label: `${e.experiment_no} · ${e.title}`, value: e.id }))
  }

  return (
    <ModalForm<FormValues>
      title={isEdit ? '编辑日报' : '新建日报'}
      trigger={<span>{trigger}</span>}
      formRef={formRef}
      width={680}
      modalProps={{ destroyOnHidden: true }}
      initialValues={initialValues}
      onFinish={async (values) => {
        const payload: DailyReportInput = {
          report_date: values.report_date,
          items: values.items.map((item, index) => ({ ...item, sort_order: index })),
        }
        try {
          if (isEdit && report) {
            await dailyReportService.updateReport(report.id, payload, currentUser.id)
            message.success('日报已保存')
          } else {
            await dailyReportService.createReport(payload, currentUser.id)
            message.success('日报草稿已创建')
          }
          onSaved?.()
          return true
        } catch (error) {
          message.error((error as ApiError).message || '保存失败')
          return false
        }
      }}
    >
      <ProFormText
        name="submitter_display"
        label="提交人"
        initialValue={`${currentUser.full_name}（${currentUser.username}）`}
        disabled
        tooltip="提交人固定为当前登录用户"
      />
      <ProFormDatePicker
        name="report_date"
        label="日期"
        rules={[{ required: true, message: '请选择日期' }]}
        width="md"
      />
      <ProFormList
        name="items"
        label="工作明细"
        creatorButtonProps={{ creatorButtonText: '添加工作明细' }}
        copyIconProps={false}
        min={1}
        itemRender={({ listDom, action }, { index }) => (
          <div style={{ border: '1px solid #e8e1d8', borderRadius: 8, padding: 16, marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <strong>明细 {index + 1}</strong>
              {action}
            </div>
            {listDom}
          </div>
        )}
        initialValue={initialValues.items}
      >
        <ProFormSelect
          name="project_id"
          label="所属项目"
          rules={[{ required: true, message: '请选择所属项目' }]}
          request={projectOptions}
          fieldProps={{ showSearch: true, optionFilterProp: 'label' }}
        />
        <ProFormSelect
          name="work_type"
          label="工作类型"
          options={[
            { label: '实验', value: 'experiment' },
            { label: '分析', value: 'analysis' },
            { label: '纯化', value: 'purification' },
            { label: '文档', value: 'documentation' },
            { label: '会议', value: 'meeting' },
            { label: '库存', value: 'inventory' },
            { label: '其他', value: 'other' },
          ]}
          initialValue="other"
          rules={[{ required: true }]}
        />
          <ProFormSelect
            name="experiment_record_id"
            label="关联实验记录"
            request={experimentOptions}
            fieldProps={{ showSearch: true, optionFilterProp: 'label', allowClear: true }}
            tooltip="可选；提交时后端会校验实验与项目一致"
          />
      <ProFormTextArea
        name="content"
        label="工作内容"
        rules={[{ required: true, message: '请填写工作内容' }]}
        fieldProps={{ rows: 3 }}
      />
        <ProFormTextArea name="problem_note" label="问题与风险" fieldProps={{ rows: 2 }} />
        <ProFormTextArea name="next_step" label="明日计划" fieldProps={{ rows: 2 }} />
      </ProFormList>
      <Alert
        type="info"
        showIcon
        message="附件/图谱为占位，暂不支持真实上传（后续接入 MinIO）。"
      />
    </ModalForm>
  )
}
