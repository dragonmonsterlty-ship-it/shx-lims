import { fileURLToPath, URL } from 'node:url'

import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
  },
  build: {
    // 路由已按页面懒加载；此处再把大型第三方库拆分为独立 vendor chunk（利于缓存）。
    // antd 组件库本体约 1.5MB（gzip ~465KB）是组件密集后台的固有体量，作为已知 vendor
    // 地板；业务页面均已懒加载为独立小 chunk。阈值据实设为 1600KB 以保持 build 干净。
    chunkSizeWarningLimit: 1600,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'antd-vendor': ['antd', '@ant-design/icons'],
          'pro-vendor': ['@ant-design/pro-components'],
          'query-vendor': ['@tanstack/react-query'],
        },
      },
    },
  },
})
