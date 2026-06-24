# LIMS Frontend

LIMS 前端单页应用：React 18 + TypeScript + antd v5 + Ant Design Pro 组件 +
React Query + axios + react-router。详见根目录 `CLAUDE.md` 技术栈约定。

## 开发

```bash
npm install        # 安装依赖
npm run dev        # 本地开发 (http://localhost:5173)
npm run typecheck  # tsc --noEmit 类型检查
npm run lint       # eslint
npm run build      # 类型检查 + 生产构建
npm run preview    # 预览构建产物
```

## 后端对接

复制环境变量模板：

```powershell
Copy-Item .env.example .env.local
```

默认配置：

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:18000/api
VITE_API_MODE=real
```

- `VITE_API_BASE_URL`：后端 `/api` 基址。后端端口改变时只修改该变量，不改页面代码。
- `VITE_API_MODE=real`：使用真实 JWT 后端。
- `VITE_API_MODE=mock`：使用前端内置 mock；不会同时请求真实后端。
- real 模式不做隐式 mock fallback，避免无法判断数据来源。

启动前端：

```powershell
npm.cmd install
npm.cmd run dev
```

后端推荐地址为 `http://127.0.0.1:18000/api`。后端响应统一为
`{ code, message, data }`，分页 `data` 为
`{ items, total, page, page_size }`。

## 联调验证

后端迁移、demo seed 和服务启动后运行：

```powershell
npm.cmd run verify:api
```

如后端不在 `18000`：

```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000/api"
npm.cmd run verify:api
```

脚本使用 `admin/password123` 登录，可用 `LIMS_VERIFY_USERNAME` 和
`LIMS_VERIFY_PASSWORD` 覆盖。它只读取 health、项目、负责人候选、实验、日报、
试剂和批次，不写后端数据。

## 常见问题

- **CORS**：后端 `CORS_ORIGINS` 需包含前端 Origin，默认开发地址通常是
  `http://localhost:5173` 或 `http://127.0.0.1:5173`。
- **端口错误**：页面显示“无法连接后端 API”时，检查服务监听端口并修改
  `VITE_API_BASE_URL`。
- **响应包裹层**：页面和 service 不直接读取 Axios response；统一 API client
  解包 `{code,message,data}`，`code !== 0` 转为 `ApiError`。
- **分页字段**：列表 service 统一消费 `items/total/page/page_size`，后端单页最大
  `page_size=100`。
- **401/403**：检查登录 token、当前账号角色与项目访问范围；错误会显示在页面，
  不会回退到 mock。
