import { PlusOutlined } from '@ant-design/icons'
import {
  PageContainer,
  ProTable,
  type ActionType,
  type ProColumns,
} from '@ant-design/pro-components'
import { useQuery } from '@tanstack/react-query'
import { Alert, Button } from 'antd'
import { useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '../../auth/useAuth'
import { can, canEditProject } from '../../auth/permissions'
import StatusTag from '../../components/StatusTag'
import { useUsers } from '../../hooks/useUsers'
import { projectService } from '../../services/project'
import { userService } from '../../services/user'
import type { Id, Project, ProjectStatus } from '../../types'
import { formatDate } from '../../utils/format'
import ProjectFormModal from './ProjectFormModal'

interface ProjectParams {
  project_code?: string
  name?: string
  project_type?: string
  status?: ProjectStatus
  lead_user_id?: Id
  priority?: string
}

const PROJECT_TYPE_OPTIONS = [
  { label: '稳定性', value: '稳定性' },
  { label: '质量研究', value: '质量研究' },
  { label: '工艺', value: '工艺' },
  { label: '小试路线', value: '小试路线' },
]

const STATUS_OPTIONS = [
  { label: '进行中', value: 'active' },
  { label: '暂停', value: 'paused' },
  { label: '已完成', value: 'completed' },
  { label: '已终止', value: 'cancelled' },
]

const PRIORITY_OPTIONS = [
  { label: '普通', value: 'normal' },
  { label: '高', value: 'high' },
  { label: '紧急', value: 'urgent' },
]

export default function ProjectListPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const { getName } = useUsers()
  const actionRef = useRef<ActionType>(null)
  const [loadError, setLoadError] = useState<string>()
  const ownerQuery = useQuery({
    queryKey: ['users', 'project-owner-candidates'],
    queryFn: () => userService.listProjectOwnerCandidates(),
  })

  const ownerOptions = useMemo(
    () =>
      (ownerQuery.data ?? [])
        .map((u) => ({ label: `${u.full_name}（${u.username}）`, value: u.id })),
    [ownerQuery.data],
  )
  const ownerNameMap = useMemo(
    () =>
      new Map<Id, string>(
        (ownerQuery.data ?? []).map((owner) => [owner.id, owner.full_name]),
      ),
    [ownerQuery.data],
  )

  if (!user) return null

  const columns: ProColumns<Project>[] = [
    {
      title: '项目代码',
      dataIndex: 'project_code',
      copyable: true,
      width: 140,
      fixed: 'left',
    },
    { title: '项目名称', dataIndex: 'name', ellipsis: true },
    {
      title: '项目类型',
      dataIndex: 'project_type',
      width: 120,
      valueType: 'select',
      fieldProps: { options: PROJECT_TYPE_OPTIONS, allowClear: true },
      render: (_, row) => row.project_type ?? '—',
    },
    {
      title: '项目负责人',
      dataIndex: 'lead_user_id',
      width: 150,
      valueType: 'select',
      fieldProps: {
        options: ownerOptions,
        allowClear: true,
        showSearch: true,
        optionFilterProp: 'label',
        placeholder: '请选择负责人',
      },
      render: (_, row) =>
        row.lead_user_id == null
          ? '—'
          : ownerNameMap.get(row.lead_user_id) ?? getName(row.lead_user_id),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      width: 90,
      valueType: 'select',
      fieldProps: { options: PRIORITY_OPTIONS, allowClear: true },
      render: (_, row) => row.priority ?? 'normal',
    },
    {
      title: '项目状态',
      dataIndex: 'status',
      width: 110,
      valueType: 'select',
      fieldProps: { options: STATUS_OPTIONS, allowClear: true },
      render: (_, row) => <StatusTag kind="project" value={row.status} />,
    },
    { title: '开始', dataIndex: 'start_date', width: 110, search: false, render: (_, r) => formatDate(r.start_date) },
    { title: '结束', dataIndex: 'end_date', width: 110, search: false, render: (_, r) => formatDate(r.end_date) },
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      fixed: 'right',
      render: (_, row) => [
        <a key="view" onClick={() => navigate(`/projects/${row.id}`)}>
          查看
        </a>,
        canEditProject(user, row) ? (
          <ProjectFormModal
            key="edit"
            mode="edit"
            currentUser={user}
            project={row}
            trigger={<a>编辑</a>}
            onSaved={() => actionRef.current?.reload()}
          />
        ) : null,
      ],
    },
  ]

  return (
    <PageContainer title="项目管理">
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
      <ProTable<Project, ProjectParams>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        scroll={{ x: 1000 }}
        cardBordered
        options={{ density: true, reload: true, setting: true }}
        pagination={{ defaultPageSize: 10, showSizeChanger: true }}
        search={{ labelWidth: 'auto', defaultCollapsed: false }}
        request={async (params) => {
          try {
            setLoadError(undefined)
            const res = await projectService.listProjects(
              {
                page: params.current,
                page_size: params.pageSize,
                project_code: params.project_code,
                name: params.name,
                project_type: params.project_type,
                status: params.status,
                lead_user_id: params.lead_user_id,
                priority: params.priority,
              },
              user,
            )
            return { data: res.items, total: res.total, success: true }
          } catch (error) {
            setLoadError((error as { message?: string }).message ?? '项目列表加载失败')
            return { data: [], total: 0, success: false }
          }
        }}
        toolBarRender={() =>
          can.createProject(user.role)
            ? [
                <ProjectFormModal
                  key="create"
                  mode="create"
                  currentUser={user}
                  trigger={
                    <Button type="primary" icon={<PlusOutlined />}>
                      新建项目
                    </Button>
                  }
                  onSaved={() => actionRef.current?.reload()}
                />,
              ]
            : []
        }
      />
    </PageContainer>
  )
}
