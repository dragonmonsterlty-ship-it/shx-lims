import { DownloadOutlined, InboxOutlined } from '@ant-design/icons'
import {
  Alert,
  App,
  Button,
  Descriptions,
  Modal,
  Space,
  Table,
  Typography,
  Upload,
  type UploadFile,
} from 'antd'
import { useState } from 'react'

import type { ApiError } from '../../api/errors'
import { inventoryService } from '../../services/inventory'
import type {
  ReagentImportIssue,
  ReagentImportResult,
  ReagentImportTemplateFormat,
} from '../../types'
import { reagentImportFileValidationMessage } from './reagentImportFile'

interface ReagentImportModalProps {
  open: boolean
  onCancel: () => void
  onImported: () => void
}

export default function ReagentImportModal({
  open,
  onCancel,
  onImported,
}: ReagentImportModalProps) {
  const { message } = App.useApp()
  const [file, setFile] = useState<File>()
  const [result, setResult] = useState<ReagentImportResult>()
  const [previewing, setPreviewing] = useState(false)
  const [importing, setImporting] = useState(false)
  const [downloading, setDownloading] = useState<ReagentImportTemplateFormat>()

  const reset = () => {
    setFile(undefined)
    setResult(undefined)
    setPreviewing(false)
    setImporting(false)
    setDownloading(undefined)
  }

  const close = () => {
    reset()
    onCancel()
  }

  const downloadTemplate = async (format: ReagentImportTemplateFormat) => {
    setDownloading(format)
    try {
      await inventoryService.downloadReagentImportTemplate(format)
    } catch (error) {
      message.error((error as ApiError).message || '模板下载失败')
    } finally {
      setDownloading(undefined)
    }
  }

  const preview = async () => {
    if (!file) return
    setPreviewing(true)
    try {
      setResult(await inventoryService.importReagentInventory(file, true))
    } catch (error) {
      setResult(undefined)
      message.error((error as ApiError).message || '预览校验失败')
    } finally {
      setPreviewing(false)
    }
  }

  const confirmImport = async () => {
    if (!file || !result || result.errors.length > 0) return
    setImporting(true)
    try {
      const imported = await inventoryService.importReagentInventory(file, false)
      if (imported.errors.length > 0) {
        setResult(imported)
        message.error('导入文件仍有错误，请修正后重新校验')
        return
      }
      message.success('导入成功')
      reset()
      onCancel()
      onImported()
    } catch (error) {
      message.error((error as ApiError).message || '导入失败')
    } finally {
      setImporting(false)
    }
  }

  const selectFile = (selected: File) => {
    const validationMessage = reagentImportFileValidationMessage(selected)
    if (validationMessage) {
      message.error(validationMessage)
      return Upload.LIST_IGNORE
    }
    setFile(selected)
    setResult(undefined)
    return false
  }

  const fileList: UploadFile[] = file
    ? [{ uid: file.name, name: file.name, status: 'done' }]
    : []

  return (
    <Modal
      title="导入试剂库存"
      open={open}
      width={900}
      onCancel={close}
      destroyOnClose
      footer={[
        <Button key="cancel" onClick={close} disabled={previewing || importing}>取消</Button>,
        <Button key="preview" onClick={preview} disabled={!file || importing} loading={previewing}>预览校验</Button>,
        <Button
          key="import"
          type="primary"
          onClick={confirmImport}
          disabled={!result || result.errors.length > 0 || previewing}
          loading={importing}
        >
          确认导入
        </Button>,
      ]}
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <div>
          <Typography.Text strong>下载中文模板</Typography.Text>
          <div style={{ marginTop: 8 }}>
            <Space wrap>
              <Button
                icon={<DownloadOutlined />}
                loading={downloading === 'csv'}
                onClick={() => downloadTemplate('csv')}
              >
                下载 CSV 模板
              </Button>
              <Button
                icon={<DownloadOutlined />}
                loading={downloading === 'xlsx'}
                onClick={() => downloadTemplate('xlsx')}
              >
                下载 Excel 模板
              </Button>
            </Space>
          </div>
        </div>

        <Upload.Dragger
          accept=".csv,.xlsx"
          multiple={false}
          maxCount={1}
          beforeUpload={selectFile}
          fileList={fileList}
          onRemove={() => {
            setFile(undefined)
            setResult(undefined)
          }}
        >
          <p className="ant-upload-drag-icon"><InboxOutlined /></p>
          <p className="ant-upload-text">点击或拖拽 CSV/Excel 文件到此区域</p>
          <p className="ant-upload-hint">仅支持单个 .csv 或 .xlsx 文件</p>
        </Upload.Dragger>

        {result ? <ImportResult result={result} /> : null}
      </Space>
    </Modal>
  )
}

function ImportResult({ result }: { result: ReagentImportResult }) {
  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Alert
        showIcon
        type={result.errors.length > 0 ? 'error' : 'success'}
        message={result.errors.length > 0 ? '校验未通过，请修正错误后重新上传' : '校验通过，可以确认导入'}
      />
      <Descriptions size="small" bordered column={{ xs: 2, sm: 3 }}>
        <Descriptions.Item label="总行数">{result.total_rows}</Descriptions.Item>
        <Descriptions.Item label="有效行数">{result.valid_rows}</Descriptions.Item>
        <Descriptions.Item label="错误行数">{result.error_rows}</Descriptions.Item>
        <Descriptions.Item label="新建试剂数">{result.created_reagents}</Descriptions.Item>
        <Descriptions.Item label="匹配已有试剂数">{result.matched_reagents}</Descriptions.Item>
        <Descriptions.Item label="新建批次数">{result.created_lots}</Descriptions.Item>
      </Descriptions>
      {result.errors.length > 0 ? (
        <IssueTable title="错误明细" messageTitle="错误信息" issues={result.errors} />
      ) : null}
      {result.warnings.length > 0 ? (
        <IssueTable title="警告明细" messageTitle="警告信息" issues={result.warnings} />
      ) : null}
    </Space>
  )
}

function IssueTable({
  title,
  messageTitle,
  issues,
}: {
  title: string
  messageTitle: string
  issues: ReagentImportIssue[]
}) {
  const columns = [
    { title: '行号', dataIndex: 'row', width: 80 },
    { title: '字段', dataIndex: 'field', width: 120 },
    { title: messageTitle, dataIndex: 'message' },
  ]
  return (
    <div>
      <Typography.Text strong>{title}</Typography.Text>
      <Table
        style={{ marginTop: 8 }}
        size="small"
        rowKey={(item, index) => `${item.row}-${item.field}-${index}`}
        columns={columns}
        dataSource={issues}
        pagination={issues.length > 5 ? { pageSize: 5, size: 'small' } : false}
        scroll={{ x: 500, y: 240 }}
      />
    </div>
  )
}
