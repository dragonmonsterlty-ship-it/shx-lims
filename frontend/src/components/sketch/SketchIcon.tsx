import type { CSSProperties, ReactNode } from 'react'

/**
 * 手账风 line-art 图标。仅用于「氛围区」（登录/注册背景、Dashboard banner 与卡片角标、
 * 列表空状态、错误页插画）。严禁进入工作区的数据容器（ProTable / ProForm / 详情字段区）。
 *
 * 实现约定（与 CLAUDE.md「前端视觉风格约定」一致）：
 * - 一律内联 SVG，stroke 风格，fill="none"，无实心填充。
 * - stroke-width 约 1.5–2，描边色用低饱和（墨蓝 #2B4C7E / 灰绿 #4A7C59 / 炭灰 #333）。
 * - 路径坐标刻意带轻微抖动，不追求精确几何，呈手绘感。
 * - 默认 aria-hidden（纯装饰）；如需语义，传 title 即转为 role="img"。
 */
export type SketchIconName =
  | 'test-tube'
  | 'flask'
  | 'brain-ai'
  | 'laptop'
  | 'qrcode'
  | 'sparkle'
  | 'reagent'
  | 'empty-box'

export interface SketchIconProps {
  name: SketchIconName
  /** 像素尺寸（宽高一致）。默认 24。 */
  size?: number
  /** 描边色。默认低饱和墨蓝；建议从白名单取色。 */
  color?: string
  /** 描边宽度，默认 1.7（1.5–2 区间）。 */
  strokeWidth?: number
  className?: string
  style?: CSSProperties
  /** 传入则视为有语义图标（role="img"），否则纯装饰（aria-hidden）。 */
  title?: string
}

/** 每个图标只画描边路径，颜色/线宽由外层 <svg> 继承。 */
const PATHS: Record<SketchIconName, ReactNode> = {
  'test-tube': (
    <>
      {/* 管口斜唇 + 管身 + 圆底 */}
      <path d="M7.6 3.4 Q12 2.1 16.6 3.5" />
      <path d="M8.4 3.7 L8.1 16.2 a3.9 3.9 0 0 0 7.8 0 L15.5 3.6" />
      {/* 液面波纹（非填充） */}
      <path d="M8.3 12.1 q2 1.1 3.9 0.1 t3.7 -0.2" />
      <circle cx="10.4" cy="14.6" r="0.5" />
      <circle cx="13.1" cy="16.2" r="0.45" />
    </>
  ),
  flask: (
    <>
      {/* 瓶颈 + 唇口 */}
      <path d="M9.4 3.1 L14.7 3" />
      <path d="M10.1 3.3 L10 9.1" />
      <path d="M14 3.2 L14.1 9" />
      {/* 锥形瓶体 */}
      <path d="M10 9.1 L5.2 18.6 Q4.7 20.6 6.8 20.6 L17.3 20.6 Q19.4 20.6 18.8 18.6 L14.1 9" />
      {/* 液面 */}
      <path d="M6.7 16.2 q2.6 1.3 5.3 0.2 t5.2 -0.4" />
    </>
  ),
  'brain-ai': (
    <>
      {/* 脑轮廓（左右对称双叶） */}
      <path d="M12 6 C9.7 4.6 6.7 5.4 6.2 7.9 C4.3 8.3 4.2 10.9 5.9 11.7 C5.3 13.7 7.2 15.3 9.3 14.6 C9.9 15.8 11.1 16 12 15.4" />
      <path d="M12 6 C14.3 4.6 17.3 5.4 17.8 7.9 C19.7 8.3 19.8 10.9 18.1 11.7 C18.7 13.7 16.8 15.3 14.7 14.6 C14.1 15.8 12.9 16 12 15.4" />
      <path d="M12 6.2 L12 15.3" />
      {/* AI 神经节点 + 连线 */}
      <circle cx="9.1" cy="9.6" r="0.7" />
      <circle cx="14.9" cy="9.6" r="0.7" />
      <circle cx="12" cy="12.4" r="0.7" />
      <path d="M9.6 10 L11.5 12" />
      <path d="M14.4 10 L12.5 12" />
    </>
  ),
  laptop: (
    <>
      {/* 屏幕 */}
      <path d="M6.2 5 L17.8 5 Q18.4 5 18.4 5.6 L18.4 13.7 L5.6 13.7 L5.6 5.6 Q5.6 5 6.2 5 Z" />
      {/* 底座 / 键盘面 */}
      <path d="M3.4 13.8 L20.6 13.8 L21.7 17.8 Q21.8 18.2 21.3 18.2 L2.7 18.2 Q2.2 18.2 2.3 17.8 Z" />
      {/* 触控板缺口 */}
      <path d="M10 18.2 L14 18.2" />
    </>
  ),
  qrcode: (
    <>
      {/* 外框 */}
      <path d="M5.2 5.1 L18.8 5 Q19 5 19 5.2 L18.9 18.8 L5.1 18.9 Q5 18.9 5 18.7 Z" />
      {/* 三个定位角 */}
      <path d="M7 7 L10.1 6.9 L10 10 L6.9 10.1 Z" />
      <rect x="8.1" y="8" width="1" height="1" rx="0.2" />
      <path d="M14 6.9 L17.1 7 L17 10.1 L13.9 10 Z" />
      <rect x="15" y="8" width="1" height="1" rx="0.2" />
      <path d="M7 14 L10.1 13.9 L10 17 L6.9 17.1 Z" />
      <rect x="8" y="15" width="1" height="1" rx="0.2" />
      {/* 散落模块 */}
      <rect x="13.6" y="13.7" width="1.4" height="1.4" rx="0.2" />
      <rect x="16.1" y="13.8" width="1.2" height="1.2" rx="0.2" />
      <rect x="15.4" y="16" width="1.4" height="1.4" rx="0.2" />
      <rect x="13.5" y="16.4" width="1" height="1" rx="0.2" />
    </>
  ),
  sparkle: (
    <>
      {/* 四角星（凹边） */}
      <path d="M12 3.6 C12.5 8 13.2 9.6 17.4 11 C13.2 12.4 12.5 14 12 18.4 C11.5 14 10.8 12.4 6.6 11 C10.8 9.6 11.5 8 12 3.6 Z" />
      {/* 小辅星 */}
      <path d="M18.4 4.2 C18.6 5.6 18.9 6 20.2 6.4 C18.9 6.8 18.6 7.2 18.4 8.6 C18.2 7.2 17.9 6.8 16.6 6.4 C17.9 6 18.2 5.6 18.4 4.2 Z" />
    </>
  ),
  reagent: (
    <>
      {/* 瓶盖 */}
      <path d="M9.8 3 L14.3 3 L14.3 5 L9.8 5 Z" />
      {/* 瓶身（肩部收窄） */}
      <path d="M10.1 5 L10.1 7 L8.1 9 L8.1 19 Q8.1 20.6 9.7 20.6 L14.4 20.6 Q16 20.6 16 19 L16 9 L13.9 7 L13.9 5" />
      {/* 标签 */}
      <path d="M9 12 L15.1 11.9 L15 16 L8.9 16.1 Z" />
      <path d="M10.4 13.6 L13.6 13.5" />
      <path d="M10.4 14.9 L12.7 14.85" />
    </>
  ),
  'empty-box': (
    <>
      {/* 箱体（开口箱） */}
      <path d="M5 10.1 L19 10 L17.6 20 Q17.5 20.4 17.1 20.4 L6.9 20.4 Q6.5 20.4 6.4 20 Z" />
      {/* 外翻的箱盖 */}
      <path d="M5 10.1 L2.6 6.6 L9 8" />
      <path d="M19 10 L21.4 6.6 L15 8" />
      <path d="M9 8 L15 8" />
      {/* 内沿（强调空） */}
      <path d="M7 11.2 q5 1.4 10 0" />
    </>
  ),
}

export default function SketchIcon({
  name,
  size = 24,
  color = '#2B4C7E',
  strokeWidth = 1.7,
  className,
  style,
  title,
}: SketchIconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={style}
      role={title ? 'img' : undefined}
      aria-hidden={title ? undefined : true}
      focusable="false"
    >
      {title ? <title>{title}</title> : null}
      {PATHS[name]}
    </svg>
  )
}
