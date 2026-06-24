import { ModalForm, ProFormTextArea } from '@ant-design/pro-components'
import { App, Popconfirm, Space } from 'antd'

import type { ApiError } from '../../api/errors'
import type { ProjectScope } from '../../auth/permissions'
import { canConfirmReport, canEditReport } from '../../auth/permissions'
import { dailyReportService } from '../../services/dailyReport'
import type { DailyReport, User } from '../../types'

interface ReportActionsProps {
  report: DailyReport
  currentUser: User
  scope: ProjectScope
  onChanged?: () => void
}

/** 日报状态操作：编辑入口由调用方提供；此处负责 提交 / 确认 / 退回。 */
export default function ReportActions({ report, currentUser, scope, onChanged }: ReportActionsProps) {
  const { message } = App.useApp()
  const editable = canEditReport(currentUser, report)
  const reviewable = canConfirmReport(currentUser, report, scope)

  const handleSubmit = async () => {
    try {
      await dailyReportService.submitReport(report.id, currentUser.id)
      message.success('日报已提交')
      onChanged?.()
    } catch (error) {
      message.error((error as ApiError).message || '提交失败')
    }
  }

  const handleConfirm = async () => {
    try {
      await dailyReportService.confirmReport(report.id, undefined, currentUser.id)
      message.success('日报已确认')
      onChanged?.()
    } catch (error) {
      message.error((error as ApiError).message || '确认失败')
    }
  }

  if (!editable && !reviewable) return null

  return (
    <Space>
      {editable ? (
        <Popconfirm title="确认提交该日报？" onConfirm={handleSubmit} okText="提交" cancelText="取消">
          <a>提交</a>
        </Popconfirm>
      ) : null}
      {reviewable ? (
        <Popconfirm title="确认该日报？" onConfirm={handleConfirm} okText="确认" cancelText="取消">
          <a>确认</a>
        </Popconfirm>
      ) : null}
      {reviewable ? (
        <ModalForm
          title="退回日报"
          width={420}
          trigger={<a>退回</a>}
          modalProps={{ destroyOnHidden: true }}
          onFinish={async (values: { review_comment: string }) => {
            try {
              await dailyReportService.returnReport(report.id, values.review_comment, currentUser.id)
              message.success('日报已退回')
              onChanged?.()
              return true
            } catch (error) {
              message.error((error as ApiError).message || '退回失败')
              return false
            }
          }}
        >
          <ProFormTextArea
            name="review_comment"
            label="退回原因"
            rules={[{ required: true, message: '请填写退回原因' }]}
            fieldProps={{ rows: 3 }}
          />
        </ModalForm>
      ) : null}
    </Space>
  )
}
