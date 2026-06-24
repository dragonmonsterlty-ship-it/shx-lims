import { Tag } from 'antd'

import { getStatusMeta, type StatusKind } from './status'

interface StatusTagProps {
  kind: StatusKind
  value?: string | null
}

/** 统一状态标签。空值显示占位短横。 */
export default function StatusTag({ kind, value }: StatusTagProps) {
  if (!value) return <span style={{ color: 'var(--ink-muted)' }}>—</span>
  const meta = getStatusMeta(kind, value)
  return (
    <Tag color={meta.color} style={{ marginInlineEnd: 0 }}>
      {meta.label}
    </Tag>
  )
}
