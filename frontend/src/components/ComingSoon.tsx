import { PageContainer } from '@ant-design/pro-components'
import { Empty } from 'antd'

interface ComingSoonProps {
  title: string
  description?: string
  /** 计划提供的能力，列出让占位页不至于空白。 */
  planned?: string[]
}

/** 未实现模块的高质量占位页（非空白）。 */
export default function ComingSoon({ title, description, planned }: ComingSoonProps) {
  return (
    <PageContainer title={title} content={description ?? '该模块规划中，下方为预期能力。'}>
      <div className="app-center-state">
        <Empty
          description={
            <div style={{ maxWidth: 420 }}>
              <p style={{ marginBottom: planned?.length ? 12 : 0 }}>模块建设中，敬请期待</p>
              {planned?.length ? (
                <ul style={{ textAlign: 'left', color: 'var(--ink-muted)', margin: 0, paddingLeft: 18 }}>
                  {planned.map((p) => (
                    <li key={p}>{p}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          }
        />
      </div>
    </PageContainer>
  )
}
