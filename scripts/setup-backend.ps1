# 后端一次性准备：虚拟环境 + 依赖 + 迁移 + demo seed
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$be = Join-Path $root 'backend'
Push-Location $be
try {
  if (-not (Test-Path '.\.venv')) { python -m venv .venv }
  $py = '.\.venv\Scripts\python.exe'
  & $py -m pip install --upgrade pip
  & $py -m pip install -r requirements.txt -r requirements-dev.txt
  if (-not (Test-Path '.\.env')) { Copy-Item (Join-Path $root '.env.example') '.\.env' }
  & $py -m alembic upgrade head
  & $py scripts\seed_demo.py
  Write-Host '后端就绪：依赖已安装，数据库已迁移并写入 demo 数据。'
} finally {
  Pop-Location
}
