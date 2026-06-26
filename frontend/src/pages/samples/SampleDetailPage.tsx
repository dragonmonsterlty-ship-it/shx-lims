import {
  ModalForm,
  PageContainer,
  ProFormDatePicker,
  ProFormSelect,
  ProFormTextArea,
} from '@ant-design/pro-components'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Button, Card, Descriptions, Popconfirm, Space, Table, Tabs } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { ReactNode } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import type { ApiError } from '../../api/errors'
import {
  canDeleteAttachment,
  canExecuteTestTask,
  canManageSample,
  canUploadAttachment,
} from '../../auth/permissions'
import { AttachmentPanel } from '../../components/attachments'
import { useAuth } from '../../auth/useAuth'
import QueryBoundary from '../../components/QueryBoundary'
import StatusTag from '../../components/StatusTag'
import { SketchEmpty } from '../../components/sketch'
import { useProjectScope } from '../../hooks/useProjectScope'
import { useUsers } from '../../hooks/useUsers'
import { projectService } from '../../services/project'
import { resultService } from '../../services/result'
import { sampleService } from '../../services/sample'
import type { Id, ResultDraftInput, TestTask } from '../../types'
import { formatDate, formatDateTime } from '../../utils/format'
import SampleFormModal from './SampleFormModal'

function TaskForm({
  sampleId,
  projectId,
  trigger,
  onSaved,
}: {
  sampleId: Id
  projectId: Id
  trigger: ReactNode
  onSaved: () => void
}) {
  const { message } = App.useApp()
  return (
    <ModalForm<{ method_id: Id; assigned_to: Id; priority: string; due_date?: string }>
      title="创建检测任务"
      trigger={<span>{trigger}</span>}
      width={500}
      modalProps={{ destroyOnHidden: true }}
      initialValues={{ priority: 'normal' }}
      onFinish={async (values) => {
        try {
          await sampleService.createTestTask({ sample_id: sampleId, ...values })
          message.success('检测任务已创建')
          onSaved()
          return true
        } catch (error) {
          message.error((error as ApiError).message || '创建失败')
          return false
        }
      }}
    >
      <ProFormSelect
        name="method_id"
        label="检测方法"
        rules={[{ required: true, message: '请选择检测方法' }]}
        request={async () =>
          (await sampleService.listTestMethods()).map((method) => ({
            label: `${method.code} · ${method.name}${method.version ? `（${method.version}）` : ''}`,
            value: method.id,
          }))
        }
      />
      <ProFormSelect
        name="assigned_to"
        label="负责人"
        rules={[{ required: true, message: '请选择负责人' }]}
        request={async () =>
          (await projectService.listMembers(projectId))
            .filter((member) => member.user?.role === 'operator')
            .map((member) => ({
              label: member.user?.full_name ?? `#${member.user_id}`,
              value: member.user_id,
            }))
        }
      />
      <ProFormSelect
        name="priority"
        label="优先级"
        options={[
          { label: '普通', value: 'normal' },
          { label: '高', value: 'high' },
        ]}
      />
      <ProFormDatePicker name="due_date" label="截止日期" />
    </ModalForm>
  )
}

function AssigneeForm({
  task,
  trigger,
  onSaved,
}: {
  task: TestTask
  trigger: ReactNode
  onSaved: () => void
}) {
  const { message } = App.useApp()
  return (
    <ModalForm<{ assigned_to: Id }>
      title="重新分配检测任务"
      trigger={<span>{trigger}</span>}
      width={440}
      modalProps={{ destroyOnHidden: true }}
      initialValues={{ assigned_to: task.assigned_to }}
      onFinish={async (values) => {
        try {
          await sampleService.updateTaskAssignee(task.id, values.assigned_to)
          message.success('负责人已更新')
          onSaved()
          return true
        } catch (error) {
          message.error((error as ApiError).message || '分配失败')
          return false
        }
      }}
    >
      <ProFormSelect
        name="assigned_to"
        label="负责人"
        rules={[{ required: true }]}
        request={async () =>
          (await projectService.listMembers(task.sample.project_id))
            .filter((member) => member.user?.role === 'operator')
            .map((member) => ({ label: member.user?.full_name ?? `#${member.user_id}`, value: member.user_id }))
        }
      />
    </ModalForm>
  )
}

function ResultForm({
  task,
  trigger,
  onSaved,
}: {
  task: TestTask
  trigger: ReactNode
  onSaved: () => void
}) {
  const { message } = App.useApp()
  const resultQuery = useQuery({
    queryKey: ['test-result', task.result_id],
    queryFn: () => resultService.getResult(task.result_id!),
    enabled: !!task.result_id,
  })
  const result = resultQuery.data
  const initialJson = result?.result_data ? JSON.stringify(result.result_data, null, 2) : '{\n  "value": ""\n}'

  return (
    <ModalForm<{ result_json: string; conclusion?: string }>
      title={task.result_id ? '编辑检测结果' : '录入检测结果'}
      trigger={<span>{trigger}</span>}
      width={620}
      modalProps={{ destroyOnHidden: true }}
      initialValues={{ result_json: initialJson, conclusion: result?.conclusion ?? '' }}
      onFinish={async (values) => {
        let resultData: unknown
        try {
          resultData = JSON.parse(values.result_json)
        } catch {
          message.error('result_data 必须是合法 JSON')
          return false
        }
        const payload: ResultDraftInput = { result_data: resultData, conclusion: values.conclusion }
        try {
          await resultService.saveDraft(task.id, payload, task.result_id)
          message.success('结果草稿已保存')
          onSaved()
          return true
        } catch (error) {
          message.error((error as ApiError).message || '保存失败')
          return false
        }
      }}
    >
      <ProFormTextArea
        name="result_json"
        label="result_data（JSON）"
        rules={[{ required: true, message: '请填写结果数据' }]}
        fieldProps={{ rows: 9 }}
      />
      <ProFormTextArea name="conclusion" label="结论" fieldProps={{ rows: 3 }} />
    </ModalForm>
  )
}

export default function SampleDetailPage() {
  const { id } = useParams()
  const sampleId = Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { message } = App.useApp()
  const { user } = useAuth()
  const { scope } = useProjectScope(user)
  const { getName } = useUsers()

  const sampleQuery = useQuery({
    queryKey: ['sample', sampleId],
    queryFn: () => sampleService.getSample(sampleId),
    enabled: Number.isFinite(sampleId),
  })
  const sample = sampleQuery.data
  const projectQuery = useQuery({
    queryKey: ['project', sample?.project_id],
    queryFn: () => projectService.getProject(sample!.project_id),
    enabled: !!sample,
  })
  const tasksQuery = useQuery({
    queryKey: ['sample', sampleId, 'tasks'],
    queryFn: () => sampleService.listSampleTests(sampleId),
    enabled: Number.isFinite(sampleId),
  })

  if (!user) return null
  const manageable = sample ? canManageSample(user, sample.project_id, scope) : false
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['sample', sampleId] })
    queryClient.invalidateQueries({ queryKey: ['sample', sampleId, 'tasks'] })
  }

  const columns: ColumnsType<TestTask> = [
    { title: '方法编号', dataIndex: ['method', 'code'], width: 120 },
    { title: '检测项', dataIndex: ['method', 'name'], ellipsis: true },
    { title: '版本', dataIndex: ['method', 'version'], width: 90, render: (value) => value ?? '—' },
    { title: '负责人', dataIndex: 'assigned_to', width: 110, render: (value) => getName(value) },
    { title: '任务状态', dataIndex: 'status', width: 100, render: (value) => <StatusTag kind="test" value={value} /> },
    { title: '结果状态', dataIndex: 'result_status', width: 100, render: (value) => <StatusTag kind="review" value={value} /> },
    { title: '截止日期', dataIndex: 'due_date', width: 110, render: (value) => formatDate(value) },
    {
      title: '操作',
      key: 'actions',
      width: 250,
      render: (_, task) => {
        const actions: ReactNode[] = []
        if (manageable && !['completed', 'cancelled'].includes(task.status)) {
          actions.push(<AssigneeForm key="assign" task={task} trigger={<a>分配</a>} onSaved={refresh} />)
          actions.push(
            <Popconfirm
              key="cancel"
              title="确认取消该任务？"
              onConfirm={async () => {
                await sampleService.changeTaskStatus(task.id, 'cancelled')
                refresh()
              }}
            >
              <a>取消</a>
            </Popconfirm>,
          )
        }
        if (canExecuteTestTask(user, task) && task.status === 'pending') {
          actions.push(
            <a
              key="start"
              onClick={async () => {
                try {
                  await sampleService.changeTaskStatus(task.id, 'in_progress')
                  message.success('任务已开始')
                  refresh()
                } catch (error) {
                  message.error((error as ApiError).message || '状态更新失败')
                }
              }}
            >
              开始
            </a>,
          )
        }
        if (canExecuteTestTask(user, task) && task.status === 'in_progress' && task.result_status !== 'submitted') {
          actions.push(<ResultForm key="result" task={task} trigger={<a>录入结果</a>} onSaved={refresh} />)
        }
        if (task.assigned_to === user.id && task.result_id && task.result_status === 'draft') {
          actions.push(
            <Popconfirm
              key="submit"
              title="确认提交结果审核？"
              onConfirm={async () => {
                await resultService.submitResult(task.result_id!)
                message.success('结果已提交')
                refresh()
              }}
            >
              <a>提交结果</a>
            </Popconfirm>,
          )
        }
        return <Space wrap>{actions.length ? actions : '—'}</Space>
      },
    },
  ]

  const sampleAttachmentContext = sample
    ? {
        entityType: 'sample' as const,
        projectId: sample.project_id,
        editable: !['completed', 'cancelled'].includes(sample.status),
      }
    : null

  return (
    <PageContainer
      title="样品详情"
      onBack={() => navigate('/samples')}
      extra={
        <Space>
          {sample && manageable ? (
            <SampleFormModal mode="edit" currentUser={user} sample={sample} onSaved={refresh} trigger={<Button>编辑样品</Button>} />
          ) : null}
          <Button onClick={() => navigate('/samples')}>返回列表</Button>
        </Space>
      }
    >
      <QueryBoundary
        loading={sampleQuery.isLoading}
        error={sampleQuery.error}
        onRetry={() => sampleQuery.refetch()}
        isEmpty={!sample}
        emptyText="样品不存在或无权访问"
      >
        {sample ? (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Card>
              <Descriptions
                column={{ xs: 1, sm: 2, lg: 3 }}
                title={
                  <Space>
                    <span>{sample.sample_no}</span>
                    <StatusTag kind="sample" value={sample.status} />
                  </Space>
                }
              >
                <Descriptions.Item label="样品名称">{sample.name}</Descriptions.Item>
                <Descriptions.Item label="所属项目">
                  {projectQuery.data ? `${projectQuery.data.project_code} · ${projectQuery.data.name}` : `#${sample.project_id}`}
                </Descriptions.Item>
                <Descriptions.Item label="样品类型">{sample.type ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="批号">{sample.batch_no ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="来源">{sample.source ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="数量">
                  {sample.amount == null ? '—' : `${sample.amount} ${sample.unit ?? ''}`}
                </Descriptions.Item>
                <Descriptions.Item label="储存条件">{sample.storage_condition ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="截止日期">{formatDate(sample.due_date)}</Descriptions.Item>
                <Descriptions.Item label="最近更新">{formatDateTime(sample.updated_at ?? sample.created_at)}</Descriptions.Item>
              </Descriptions>
            </Card>
            <Card>
              <Tabs
                items={[
                  {
                    key: 'tasks',
                    label: `检测任务（${tasksQuery.data?.length ?? 0}）`,
                    children: (
                      <Table<TestTask>
                        rowKey="id"
                        size="small"
                        columns={columns}
                        dataSource={tasksQuery.data ?? []}
                        loading={tasksQuery.isLoading}
                        expandable={{
                          expandedRowRender: (task) => {
                            const taskContext = {
                              entityType: 'test_task' as const,
                              projectId: task.sample.project_id,
                              editable: !['completed', 'cancelled'].includes(task.status),
                              assignedTo: task.assigned_to,
                            }
                            const resultContext = {
                              entityType: 'test_result' as const,
                              projectId: task.sample.project_id,
                              editable: task.result_status === 'draft' || task.result_status === 'rejected',
                              assignedTo: task.assigned_to,
                            }
                            return (
                              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                                <AttachmentPanel
                                  entityType="test_task"
                                  entityId={task.id}
                                  canUpload={canUploadAttachment(user, taskContext, scope)}
                                  canDelete={(attachment) =>
                                    canDeleteAttachment(user, attachment, taskContext, scope)
                                  }
                                />
                                {task.result_id ? (
                                  <AttachmentPanel
                                    entityType="test_result"
                                    entityId={task.result_id}
                                    canUpload={canUploadAttachment(user, resultContext, scope)}
                                    canDelete={(attachment) =>
                                      canDeleteAttachment(user, attachment, resultContext, scope)
                                    }
                                  />
                                ) : null}
                              </Space>
                            )
                          },
                        }}
                        pagination={false}
                        scroll={{ x: 1050 }}
                        locale={{ emptyText: <SketchEmpty description="该样品暂无检测任务" /> }}
                      />
                    ),
                  },
                  {
                    key: 'attachments',
                    label: '附件',
                    children: sampleAttachmentContext ? (
                      <AttachmentPanel
                        entityType="sample"
                        entityId={sample.id}
                        canUpload={canUploadAttachment(user, sampleAttachmentContext, scope)}
                        canDelete={(attachment) =>
                          canDeleteAttachment(user, attachment, sampleAttachmentContext, scope)
                        }
                      />
                    ) : null,
                  },
                  {
                    key: 'info',
                    label: '备注',
                    children: sample.notes ?? '—',
                  },
                ]}
              />
              {manageable ? (
                <div style={{ marginTop: 16 }}>
                  <TaskForm
                    sampleId={sample.id}
                    projectId={sample.project_id}
                    trigger={<Button type="primary">创建检测任务</Button>}
                    onSaved={refresh}
                  />
                </div>
              ) : null}
            </Card>
          </Space>
        ) : null}
      </QueryBoundary>
    </PageContainer>
  )
}
