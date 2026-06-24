import { PageContainer } from '@ant-design/pro-components'
import { useQuery } from '@tanstack/react-query'
import {
  App,
  Button,
  Descriptions,
  Popconfirm,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd'
import { useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import type { ApiError } from '../../api/errors'
import { useAuth } from '../../auth/useAuth'
import { canManageMembers, roleLabel } from '../../auth/permissions'
import QueryBoundary from '../../components/QueryBoundary'
import StatusTag from '../../components/StatusTag'
import { useUsers } from '../../hooks/useUsers'
import { projectService } from '../../services/project'
import type { Id, ProjectMember } from '../../types'
import { formatDate } from '../../utils/format'

const { Text } = Typography

export default function ProjectDetailPage() {
  const { id } = useParams()
  const projectId = Number(id)
  const { user } = useAuth()
  const navigate = useNavigate()
  const { getName, data: users } = useUsers()
  const { message } = App.useApp()

  const [newUserId, setNewUserId] = useState<Id>()

  const projectQuery = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectService.getProject(projectId),
    enabled: Number.isFinite(projectId),
  })
  const membersQuery = useQuery({
    queryKey: ['project', projectId, 'members'],
    queryFn: () => projectService.listMembers(projectId),
    enabled: Number.isFinite(projectId),
  })

  const project = projectQuery.data
  const canManage = !!user && !!project && canManageMembers(user, project)

  const allMembers = useMemo(() => membersQuery.data ?? [], [membersQuery.data])
  const memberRows = useMemo(
    () => allMembers.filter((m) => m.role_in_project === 'member'),
    [allMembers],
  )
  const memberUserIds = useMemo(() => new Set(allMembers.map((m) => m.user_id)), [allMembers])
  // 组员候选：操作员、尚未加入、且非负责人。
  const candidateOperators = (users ?? []).filter(
    (u) => u.role === 'operator' && !memberUserIds.has(u.id) && u.id !== project?.lead_user_id,
  )

  const ownerRole = users?.find((u) => u.id === project?.lead_user_id)?.role

  const handleAdd = async () => {
    if (!user || !newUserId) return
    try {
      await projectService.addMember(projectId, newUserId, 'member', user.id)
      message.success('组员已添加')
      setNewUserId(undefined)
      membersQuery.refetch()
    } catch (error) {
      message.error((error as ApiError).message || '添加失败')
    }
  }

  const handleRemove = async (memberUserId: Id) => {
    if (!user) return
    try {
      await projectService.removeMember(projectId, memberUserId)
      message.success('组员已移除')
      membersQuery.refetch()
    } catch (error) {
      message.error((error as ApiError).message || '移除失败')
    }
  }

  const memberColumns = [
    { title: '姓名', dataIndex: 'user_id', render: (uid: Id) => getName(uid) },
    {
      title: '系统角色',
      dataIndex: 'user_id',
      key: 'sys_role',
      render: (uid: Id) => {
        const r = users?.find((u) => u.id === uid)?.role
        return r ? roleLabel[r] : '—'
      },
    },
    { title: '项目身份', key: 'proj_role', render: () => <Tag>项目组员</Tag> },
    ...(canManage
      ? [
          {
            title: '操作',
            key: 'op',
            render: (_: unknown, row: ProjectMember) => (
              <Popconfirm
                title="确认移除该组员？"
                onConfirm={() => handleRemove(row.user_id)}
                okText="移除"
                cancelText="取消"
              >
                <a>移除</a>
              </Popconfirm>
            ),
          },
        ]
      : []),
  ]

  return (
    <PageContainer
      title={project ? project.name : '项目详情'}
      onBack={() => navigate('/projects')}
      tags={project ? <StatusTag kind="project" value={project.status} /> : undefined}
    >
      <QueryBoundary
        loading={projectQuery.isLoading}
        error={projectQuery.error}
        onRetry={() => projectQuery.refetch()}
      >
        <Tabs
          items={[
            {
              key: 'overview',
              label: '基本信息',
              children: project ? (
                <Descriptions bordered column={2} size="small">
                  <Descriptions.Item label="项目代码">{project.project_code}</Descriptions.Item>
                  <Descriptions.Item label="项目名称">{project.name}</Descriptions.Item>
                  <Descriptions.Item label="类型">{project.project_type ?? '—'}</Descriptions.Item>
                  <Descriptions.Item label="负责人">{getName(project.lead_user_id)}</Descriptions.Item>
                  <Descriptions.Item label="状态">
                    <StatusTag kind="project" value={project.status} />
                  </Descriptions.Item>
                  <Descriptions.Item label="周期">
                    {formatDate(project.start_date)} ~ {formatDate(project.end_date)}
                  </Descriptions.Item>
                  <Descriptions.Item label="描述" span={2}>
                    {project.description ?? '—'}
                  </Descriptions.Item>
                </Descriptions>
              ) : null,
            },
            {
              key: 'members',
              label: '成员',
              children: (
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                  <Descriptions bordered size="small" column={1}>
                    <Descriptions.Item label="项目负责人">
                      <Space>
                        <Text strong>{getName(project?.lead_user_id)}</Text>
                        {ownerRole ? <Tag color="blue">{roleLabel[ownerRole]}</Tag> : null}
                      </Space>
                    </Descriptions.Item>
                  </Descriptions>

                  <div>
                    <Text strong>项目组员</Text>
                    {canManage ? (
                      <Space wrap style={{ marginTop: 8, marginBottom: 8, display: 'flex' }}>
                        <Select
                          placeholder="选择操作员加入"
                          style={{ width: 240 }}
                          value={newUserId}
                          onChange={setNewUserId}
                          showSearch
                          optionFilterProp="label"
                          options={candidateOperators.map((u) => ({
                            label: `${u.full_name}（${u.username}）`,
                            value: u.id,
                          }))}
                          notFoundContent="无可添加操作员"
                        />
                        <Button type="primary" disabled={!newUserId} onClick={handleAdd}>
                          添加组员
                        </Button>
                      </Space>
                    ) : null}
                    <Table
                      rowKey="id"
                      size="small"
                      style={{ marginTop: 8 }}
                      loading={membersQuery.isLoading}
                      dataSource={memberRows}
                      columns={memberColumns}
                      locale={{ emptyText: '暂无组员' }}
                      pagination={false}
                    />
                  </div>
                </Space>
              ),
            },
            {
              key: 'related',
              label: '关联数据',
              children: (
                <Space wrap>
                  <Button onClick={() => navigate(`/samples?project_id=${projectId}`)}>查看样品</Button>
                  <Button onClick={() => navigate(`/daily-reports?project_id=${projectId}`)}>查看日报</Button>
                  <Button onClick={() => navigate(`/experiments?project_id=${projectId}`)}>查看实验</Button>
                </Space>
              ),
            },
          ]}
        />
      </QueryBoundary>
    </PageContainer>
  )
}
