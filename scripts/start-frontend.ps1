# 启动前端 Vite dev（5173，real 模式连后端）
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$fe = Join-Path $root 'frontend'
Push-Location $fe
try {
  if (-not (Test-Path '.\node_modules')) { npm install }
  if (-not (Test-Path '.\.env')) { Copy-Item (Join-Path $root '.env.example') '.\.env' }
  npm run dev
} finally {
  Pop-Location
}
