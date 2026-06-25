import SketchIcon from './SketchIcon'

interface SketchEmptyProps {
  /** 一句提示文案。默认「暂无数据」。 */
  description?: string
  /** 插画尺寸，默认 72。 */
  size?: number
}

/**
 * 列表/卡片的统一空状态：手账风空盒子 + 一句提示。
 * 仅用于「无真实数据」的空容器（白名单内），供 Sample/Experiment/DailyLog/Reagent 等列表复用。
 * 用法：<ProTable locale={{ emptyText: <SketchEmpty description="暂无实验记录" /> }} />
 */
export default function SketchEmpty({ description = '暂无数据', size = 72 }: SketchEmptyProps) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 10,
        padding: '32px 0',
        color: 'var(--ink-muted)',
      }}
    >
      <SketchIcon name="empty-box" size={size} color="#9b9384" strokeWidth={1.6} />
      <span style={{ fontSize: 13 }}>{description}</span>
    </div>
  )
}
