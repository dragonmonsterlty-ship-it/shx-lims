import { DownloadOutlined, DeleteOutlined, UploadOutlined } from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Button, Popconfirm, Progress, Space, Table, Typography, Upload, message } from 'antd'
import { useState } from 'react'

import {
  deleteAttachment,
  downloadAttachmentToFile,
  listAttachments,
  uploadAttachment,
} from '../../services/attachment'
import type { Attachment, AttachmentEntity, Id } from '../../types'

const MAX_FILE_SIZE = 20 * 1024 * 1024
const BLOCKED_EXTENSIONS = new Set(['exe', 'bat', 'cmd', 'ps1', 'sh', 'js', 'mjs', 'cjs', 'html', 'htm'])

export interface AttachmentPanelProps {
  entityType: AttachmentEntity
  entityId: Id
  canUpload: boolean
  canDelete: (attachment: Attachment) => boolean
}

export function clientFileValidationMessage(file: Pick<File, 'name' | 'size'>): string | null {
  if (file.size > MAX_FILE_SIZE) return '单个文件不超过 20 MB'
  const extension = file.name.split('.').pop()?.toLowerCase()
  if (!extension) return '文件必须包含扩展名'
  if (BLOCKED_EXTENSIONS.has(extension)) return `不允许上传 .${extension} 类型文件`
  return null
}

export function AttachmentPanel({
  entityType,
  entityId,
  canUpload,
  canDelete,
}: AttachmentPanelProps) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const [uploadProgress, setUploadProgress] = useState<number | null>(null)
  const queryKey = ['attachments', entityType, entityId] as const

  const attachmentsQuery = useQuery({
    queryKey,
    queryFn: () => listAttachments(entityType, entityId),
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) =>
      uploadAttachment(entityType, entityId, file, (percent) => setUploadProgress(percent)),
    onSuccess: async () => {
      setError(null)
      setUploadProgress(null)
      message.success('附件上传成功')
      await queryClient.invalidateQueries({ queryKey })
    },
    onError: (err: { message?: string }) => {
      setUploadProgress(null)
      setError(err.message ?? '附件上传失败')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: Id) => deleteAttachment(id),
    onSuccess: async () => {
      setError(null)
      message.success('附件已删除')
      await queryClient.invalidateQueries({ queryKey })
    },
    onError: (err: { message?: string }) => setError(err.message ?? '附件删除失败'),
  })

  async function handleDownload(attachment: Attachment) {
    try {
      setError(null)
      await downloadAttachmentToFile(attachment.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : '附件下载失败')
    }
  }

  function handleBeforeUpload(file: File) {
    const validationMessage = clientFileValidationMessage(file)
    if (validationMessage) {
      setError(validationMessage)
      return false
    }
    setError(null)
    uploadMutation.mutate(file)
    return false
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Text type="secondary">
        单个文件不超过 20 MB；禁止上传 exe、bat、cmd、ps1、sh、js、html 等危险类型。
      </Typography.Text>
      {error ? <Alert showIcon type="error" message={error} /> : null}
      {canUpload ? (
        <Upload showUploadList={false} beforeUpload={handleBeforeUpload}>
          <Button icon={<UploadOutlined />} loading={uploadMutation.isPending}>
            上传附件
          </Button>
        </Upload>
      ) : null}
      {uploadProgress != null ? <Progress percent={uploadProgress} size="small" /> : null}
      <Table<Attachment>
        rowKey="id"
        size="small"
        loading={attachmentsQuery.isLoading}
        dataSource={attachmentsQuery.data ?? []}
        columns={[
          { title: '文件名', dataIndex: 'original_filename', ellipsis: true },
          { title: '类型', dataIndex: 'content_type', width: 160 },
          {
            title: '大小',
            dataIndex: 'file_size',
            width: 120,
            render: (value: number) => `${(value / 1024).toFixed(1)} KB`,
          },
          {
            title: '操作',
            width: 180,
            render: (_, attachment) => (
              <Space>
                <Button
                  size="small"
                  icon={<DownloadOutlined />}
                  onClick={() => void handleDownload(attachment)}
                >
                  下载
                </Button>
                {canDelete(attachment) ? (
                  <Popconfirm
                    title="确认删除该附件？"
                    onConfirm={() => deleteMutation.mutate(attachment.id)}
                  >
                    <Button size="small" danger icon={<DeleteOutlined />}>
                      删除
                    </Button>
                  </Popconfirm>
                ) : null}
              </Space>
            ),
          },
        ]}
        pagination={false}
      />
    </Space>
  )
}
