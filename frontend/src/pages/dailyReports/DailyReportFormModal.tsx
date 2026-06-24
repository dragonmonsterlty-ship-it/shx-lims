import {
  ModalForm,
  ProFormDatePicker,
  ProFormDependency,
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
import type { DailyReport, DailyReportInput, Id, User } from '../../types'

interface DailyReportFormModalProps {
  mode: 'create' | 'edit'
  currentUser: User
  report?: DailyReport
  trigger: ReactNode
  onSaved?: () => void
}

interface FormValues {
  report_date: string
  project_id?: Id
  related_experiment_id?: Id
  work_content: string
  issues_risks?: string
  next_plan?: string
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
          project_id: report.project_id ?? undefined,
          related_experiment_id: report.related_experiment_id ?? undefined,
          work_content: report.work_content,
          issues_risks: report.issues_risks ?? undefined,
          next_plan: report.next_plan ?? undefined,
        }
      : { report_date: dayjs().format('YYYY-MM-DD'), work_content: '' }

  const projectOptions = async () => {
    const res = await projectService.listProjects({ page_size: 200 }, currentUser)
    return res.items.map((p) => ({ label: `${p.project_code} · ${p.name}`, value: p.id }))
  }

  const experimentOptions = async (projectId?: Id) => {
    if (!projectId) return []
    const res = await experimentService.listExperiments({ project_id: projectId, page_size: 200 }, currentUser)
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
          project_id: values.project_id!,
          related_experiment_id: values.related_experiment_id ?? null,
          report_date: values.report_date,
          work_content: values.work_content,
          issues_risks: values.issues_risks ?? null,
          next_plan: values.next_plan ?? null,
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
      <ProFormSelect
        name="project_id"
        label="所属项目"
        rules={[{ required: true, message: '请选择所属项目' }]}
        request={projectOptions}
        disabled={isEdit}
        fieldProps={{
          showSearch: true,
          optionFilterProp: 'label',
          onChange: () => formRef.current?.setFieldsValue({ related_experiment_id: undefined }),
        }}
        tooltip="仅可选择你可见（负责或参与）的项目"
      />
      <ProFormDependency name={['project_id']}>
        {({ project_id }) => (
          <ProFormSelect
            name="related_experiment_id"
            label="关联实验记录"
            disabled={!project_id}
            params={{ project_id }}
            request={async () => experimentOptions(project_id)}
            fieldProps={{ showSearch: true, optionFilterProp: 'label', allowClear: true }}
            tooltip="可选，从该项目下你可见的实验记录中选择"
          />
        )}
      </ProFormDependency>
      <ProFormTextArea
        name="work_content"
        label="工作内容"
        rules={[{ required: true, message: '请填写工作内容' }]}
        fieldProps={{ rows: 4 }}
      />
      <ProFormTextArea name="issues_risks" label="问题与风险" fieldProps={{ rows: 3 }} />
      <ProFormTextArea name="next_plan" label="明日计划" fieldProps={{ rows: 3 }} />
      <Alert
        type="info"
        showIcon
        message="附件/图谱为占位，暂不支持真实上传（后续接入 MinIO）。"
      />
    </ModalForm>
  )
}
