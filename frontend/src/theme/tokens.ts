import type { ThemeConfig } from 'antd'

/**
 * LIMS 视觉基调 token。
 *
 * 取向：清爽、专业、低噪声的实验室后台。底色取微暖"纸感"米白（皮肤层），
 * 主色用低饱和"墨水蓝"，状态色保留语义但整体降饱和。不使用大面积渐变 /
 * 玻璃拟态；数据层保持清晰无衬线 + 表格数字（tabular-nums，见 global.css）。
 *
 * 这些常量同时镜像到 global.css 的 CSS 变量，供非 antd 元素复用。
 */
export const colors = {
  paper: '#F6F2E9', // 页面底（colorBgLayout）
  surface: '#FCFAF4', // 卡片/容器底（colorBgContainer）
  surfaceAlt: '#F1ECE0', // 表头等次级容器底
  ink: '#2B2A26', // 正文/数据
  inkMuted: '#5C594F', // 次要文字（仍 ≥4.5:1，不用浅灰）
  line: '#D9D2C2', // 细描边
  lineSoft: '#E7E0D0',
  accent: '#2F5D7C', // 主色：墨水蓝
  accentHover: '#3A6F92',
  accentActive: '#264C66',
  accentSoft: '#E3ECF1', // 选中行 / hover 底
  success: '#3E7C5A',
  warning: '#C2853B',
  error: '#B4453C',
} as const

/** 正文/数据无衬线字体栈（不依赖外部 webfont，纯系统字体）。 */
export const fontStack = [
  '-apple-system',
  'BlinkMacSystemFont',
  '"Segoe UI"',
  'Roboto',
  '"Helvetica Neue"',
  '"PingFang SC"',
  '"Microsoft YaHei"',
  '"Source Han Sans SC"',
  '"Noto Sans CJK SC"',
  'Arial',
  'sans-serif',
].join(', ')

export const themeConfig: ThemeConfig = {
  token: {
    colorPrimary: colors.accent,
    colorInfo: colors.accent,
    colorSuccess: colors.success,
    colorWarning: colors.warning,
    colorError: colors.error,
    colorTextBase: colors.ink,
    colorText: colors.ink,
    colorTextSecondary: colors.inkMuted,
    colorBgLayout: colors.paper,
    colorBgContainer: colors.surface,
    colorBorder: colors.line,
    colorBorderSecondary: colors.lineSoft,
    borderRadius: 8,
    fontFamily: fontStack,
    fontSize: 14,
    wireframe: false,
  },
  components: {
    Layout: {
      bodyBg: colors.paper,
      headerBg: colors.surface,
      siderBg: colors.surface,
      headerColor: colors.ink,
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: colors.accentSoft,
      itemSelectedColor: colors.accent,
      itemHoverBg: colors.accentSoft,
    },
    Table: {
      headerBg: colors.surfaceAlt,
      headerColor: colors.ink,
      rowHoverBg: colors.accentSoft,
      borderColor: colors.line,
      headerSplitColor: colors.line,
    },
  },
}
