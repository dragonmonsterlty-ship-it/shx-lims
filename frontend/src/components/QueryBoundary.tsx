import { Button, Empty, Result, Spin } from 'antd'
import type { ReactNode } from 'react'

import { isApiError } from '../api/errors'

interface QueryBoundaryProps {
  loading: boolean
  error?: unknown
  onRetry?: () => void
  isEmpty?: boolean
  emptyText?: string
  children: ReactNode
}

/** 非表格场景的统一 loading / error / empty 包裹。表格用 ProTable 自带状态。 */
export default function QueryBoundary({
  loading,
  error,
  onRetry,
  isEmpty,
  emptyText = '暂无数据',
  children,
}: QueryBoundaryProps) {
  if (loading) {
    return (
      <div className="app-center-state">
        <Spin />
      </div>
    )
  }
  if (error) {
    const message = isApiError(error) ? error.message : '加载失败，请稍后重试'
    return (
      <Result
        status="warning"
        title="加载失败"
        subTitle={message}
        extra={
          onRetry ? (
            <Button type="primary" onClick={onRetry}>
              重试
            </Button>
          ) : undefined
        }
      />
    )
  }
  if (isEmpty) {
    return (
      <div className="app-center-state">
        <Empty description={emptyText} />
      </div>
    )
  }
  return <>{children}</>
}
