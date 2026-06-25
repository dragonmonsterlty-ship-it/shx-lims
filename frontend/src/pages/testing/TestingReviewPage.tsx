import {
  ModalForm,
  PageContainer,
  ProFormTextArea,
  ProTable,
  type ActionType,
  type ProColumns,
} from '@ant-design/pro-components'
import { App, Popconfirm, Space, Typography } from 'antd'
import { useRef } from 'react'

import type { ApiError } from '../../api/errors'
import { canReviewTestResult } from '../../auth/permissions'
import { useAuth } from '../../auth/useAuth'
import StatusTag from '../../components/StatusTag'
import { SketchEmpty } from '../../components/sketch'
import { useProjectScope } from '../../hooks/useProjectScope'
import { projectService } from '../../services/project'
import { resultService } from '../../services/result'
import type { Id, ResultRow, ResultStatus } from '../../types'
import { formatDateTime } from '../../utils/format'

const { Text } = Typography

interface Params {
  project_id?: Id
  review_status?: ResultStatus
}

export default function TestingReviewPage() {
  const { user } = useAuth()
  const { scope } = useProjectScope(user)
  const { message } = App.useApp()
  const actionRef = useRef<ActionType>(null)

  if (!user) return null

  const columns: ProColumns<ResultRow>[] = [
    { title: '样品编号', dataIndex: 'sample_code', width: 150, copyable: true, search: false },
    { title: '检测方法', dataIndex: 'method_name', width: 150, search: false },
    {
      title: '所属项目',
      dataIndex: 'project_id',
      width: 180,
      valueType: 'select',
      request: async () => {
        const page = await projectService.listProjects({ page_size: 100 }, user)
        return page.items.map((project) => ({
          label: `${project.project_code} · ${project.name}`,
          value: project.id,
        }))
      },
      render: (_, row) => `#${row.project_id}`,
    },
    {
      title: '结果数据',
      dataIndex: 'result_data',
      search: false,
      render: (_, row) => (
        <Text code style={{ whiteSpace: 'pre-wrap' }}>
          {JSON.stringify(row.result_data)}
        </Text>
      ),
    },
    { title: '结论', dataIndex: 'conclusion', search: false, render: (_, row) => row.conclusion ?? '—' },
    {
      title: '状态',
      dataIndex: 'review_status',
      width: 100,
      valueType: 'select',
      initialValue: 'submitted',
      fieldProps: {
        options: [
          { label: '已提交', value: 'submitted' },
          { label: '已通过', value: 'approved' },
          { label: '已退回', value: 'rejected' },
        ],
      },
      render: (_, row) => <StatusTag kind="review" value={row.review_status} />,
    },
    {
      title: '提交时间',
      dataIndex: 'submitted_at',
      width: 160,
      search: false,
      render: (_, row) => formatDateTime(row.submitted_at),
    },
    {
      title: '操作',
      valueType: 'option',
      width: 130,
      render: (_, row) => {
        if (!canReviewTestResult(user, row.project_id, row.status, scope)) return []
        return [
          <Popconfirm
            key="approve"
            title="确认通过该检测结果？"
            onConfirm={async () => {
              try {
                await resultService.reviewResult(row.id, 'approve', undefined, user.id)
                message.success('结果已通过')
                actionRef.current?.reload()
              } catch (error) {
                message.error((error as ApiError).message || '审核失败')
              }
            }}
          >
            <a>通过</a>
          </Popconfirm>,
          <ModalForm<{ comment: string }>
            key="reject"
            title="退回检测结果"
            width={420}
            trigger={<a>退回</a>}
            modalProps={{ destroyOnHidden: true }}
            onFinish={async (values) => {
              try {
                await resultService.reviewResult(row.id, 'reject', values.comment, user.id)
                message.success('结果已退回')
                actionRef.current?.reload()
                return true
              } catch (error) {
                message.error((error as ApiError).message || '退回失败')
                return false
              }
            }}
          >
            <ProFormTextArea
              name="comment"
              label="退回原因"
              rules={[{ required: true, whitespace: true, message: '请填写退回原因' }]}
              fieldProps={{ rows: 4 }}
            />
          </ModalForm>,
        ]
      },
    },
  ]

  return (
    <PageContainer title="检测结果审核">
      <Space direction="vertical" style={{ width: '100%' }}>
        <ProTable<ResultRow, Params>
          actionRef={actionRef}
          rowKey="id"
          columns={columns}
          cardBordered
          search={{ labelWidth: 'auto' }}
          pagination={{ defaultPageSize: 10 }}
          locale={{ emptyText: <SketchEmpty description="暂无待审核检测结果" /> }}
          request={async (params) => {
            const result = await resultService.listReviewQueue(
              {
                page: params.current,
                page_size: params.pageSize,
                project_id: params.project_id,
                review_status: params.review_status ?? 'submitted',
              },
              user,
            )
            return { data: result.items, total: result.total, success: true }
          }}
        />
      </Space>
    </PageContainer>
  )
}
