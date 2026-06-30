# CLAUDE.md

实验室信息管理系统（LIMS）。`backend/` 为 FastAPI + SQLAlchemy + Alembic；
`frontend/` 为 React 18 + Vite + TypeScript + AntD 5 + AntD Pro + React Query。

## 前端视觉风格约定

> 这是约束**所有前端页面**的视觉宪法。后续每个页面都必须遵守。

### 核心原则：视觉分区，互不渗透

本系统是数据密集型实验室工具，视觉上严格分两区，绝不混用：

**A. 工作区（用户每天录数据、读数据的地方）—— 纯 AntD Pro，专业克制**

范围：所有 ProTable 列表、ProForm 表单、详情页、ProLayout 主框架、数据录入、
审核工作台、库存台账、样品 / 实验 / 结果界面。

要求：

- 字体一律用系统无衬线字体栈（见 `src/theme/tokens.ts` 的 `fontStack`），禁止任何手写体。
- 颜色、间距、圆角全部沿用 AntD Pro 默认 token（`src/theme/tokens.ts`），不做手绘化改造。
- 表格、表单、按钮保持 AntD 原生观感，保证扫视速度、读数效率、无障碍对比度。
- 禁止在工作区使用手账风边框、手绘线条、做旧纸纹背景。

**B. 边角与背景（用户"看一眼"的地方）—— 手账风点缀，仅作氛围**

允许范围（白名单，仅限以下位置）：

- 登录页 / 注册页的背景与插画
- 仪表盘（Dashboard）顶部 banner 区与各统计卡片的角标 icon
- 各模块列表的空状态（Empty State）插画
- 404 / 403 / 500 等错误页插画
- 全局页面背景的极淡纹理（米白底色 `#FBF8EF` 级别，透明度极低）

禁止范围：表格内、表单内、详情字段区、任何承载实数据的容器内一律不得出现。

### 手账风资产规范

- 风格：细线单色描边手绘（line-art），参考实验室器物——试管、烧瓶、大脑、化学分子
  笔记本电脑、二维码、四角星 sparkle 点缀。
- 实现：一律用内联 SVG 组件，stroke 风格，`stroke-width` 约 1.5–2，描边色用低饱和
  （墨蓝 `#2B4C7E` / 灰绿 `#4A7C59` / 炭灰 `#333`），不要实心填充。
- 线条手绘感：手工 SVG path 带轻微抖动（或 rough.js / roughjs 生成）；不要追求精确几何。
- 严禁引入含手写体的字体文件来"凑风格"；中文绝不使用手写体（渲染与授权双重坑）。
- 所有手账 icon 做成统一的 `<SketchIcon name="..." />` 组件，集中放 `src/components/sketch/` 下，
  便于复用与全局替换。
  登录页背景装饰层增加少量化学分子类手账线稿元素，包括苯环、极简球棍模型、抽象杂环分子等，保持低饱和、稀疏，不进入数据区。

### 已落地资产（第一批）

集中在 `src/components/sketch/`，通过 `src/components/sketch/index.ts` 导出：

- `<SketchIcon name size? color? strokeWidth? />` — line-art SVG 图标。可用 `name`：
  `test-tube`、`flask`、`brain-ai`、`laptop`、`qrcode`、`sparkle`、`reagent`、`empty-box`。
  默认纯装饰（`aria-hidden`）；传 `title` 转为 `role="img"`。
- `<SketchEmpty description? size? />` — 列表 / 卡片统一空状态（empty-box + 一句提示）。
  用法：`<ProTable locale={{ emptyText: <SketchEmpty description="暂无实验记录" /> }} />`。
  已接入 Experiment / DailyReport / Inventory 列表。

其它落地点：

- 登录页 `src/pages/auth/LoginPage.tsx`：米白背景 + 角落散布手账 icon（装饰层 `pointer-events:none`、
  `aria-hidden`、`zIndex 0`）；登录卡片本身保持 AntD 干净表单，**不做手绘**。
- 全局极淡米白纸纹：`src/theme/global.css` 的 `body` 背景，内联 SVG feTurbulence 颗粒、
  `opacity 0.05` 级别、`z` 序垫底。数据容器有不透明底色会完全盖住，**绝不渗入工作区**。

### 新增手账图标 / 用法

- 新图标：在 `SketchIcon.tsx` 的 `PATHS` 注册表里加一条描边路径，并扩展 `SketchIconName` 联合类型。
- 用色：从上面三种低饱和描边色里取，避免高饱和原色。
- 落点：先对照上面的**白名单**确认位置合法，再使用；任何承载实数据的容器内一律不得引入。
